#!/usr/bin/env python3
"""
Dead Link Checker — Scan markdown files for broken links.

Usage:
    python check_links.py <file_or_directory> [--timeout 10] [--ignore "domain1,domain2"]
"""

import re
import sys
import argparse
import concurrent.futures
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, quote
import ssl
import socket
from collections import defaultdict
from typing import Optional, Tuple, List, Dict


LINK_PATTERN = re.compile(
    r'\[([^\]]*)\]\(([^)]+)\)|'          # [text](url)
    r'(?<!\()https?://[^\s<>"\')\]]+'    # bare URL (not inside parens)
)


def find_markdown_files(path: Path) -> List[Path]:
    """Recursively find all markdown files."""
    if path.is_file():
        return [path] if path.suffix.lower() in ('.md', '.markdown') else []
    
    md_files = []
    for ext in ('*.md', '*.markdown'):
        md_files.extend(path.rglob(ext))
    return sorted(md_files)


def extract_links(content: str) -> List[Tuple[str, str]]:
    """
    Extract all links from markdown content.
    Returns list of (link_text, url) tuples.
    """
    links = []
    for match in LINK_PATTERN.finditer(content):
        if match.group(1) is not None and match.group(2):
            # Markdown link: [text](url)
            links.append((match.group(1), match.group(2)))
        elif match.group(0):
            # Bare URL
            links.append(('', match.group(0)))
    
    # Filter out non-HTTP links (anchors, mailto, relative paths, etc.)
    http_links = []
    for text, url in links:
        if url.startswith(('http://', 'https://')):
            http_links.append((text, url))
    
    return http_links


def check_link(url: str, timeout: int) -> Tuple[str, Optional[int], str]:
    """
    Check a single URL.
    Returns (url, status_code, error_message).
    """
    try:
        ctx = ssl.create_default_context()
        # Encode URL path to handle unicode/emoji in URLs
        parsed = urlparse(url)
        safe_url = parsed._replace(path=quote(parsed.path, safe='/:@!$&\'()*+,;=')).geturl()
        req = Request(safe_url, headers={
            'User-Agent': 'Mozilla/5.0 DeadLinkChecker/1.0'
        })
        with urlopen(req, timeout=timeout, context=ctx) as response:
            return (url, response.status, '')
    except HTTPError as e:
        return (url, e.code, repr(e))
    except (URLError, socket.timeout, OSError, ssl.SSLError) as e:
        return (url, None, repr(e))
    except Exception as e:
        return (url, None, f'Unexpected: {repr(e)}')


def should_ignore(url: str, ignore_domains: List[str]) -> bool:
    """Check if URL should be ignored based on domain."""
    if not ignore_domains:
        return False
    try:
        domain = urlparse(url).netloc.lower()
        return any(ignored in domain for ignored in ignore_domains)
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Dead Link Checker — Find broken links in markdown files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s README.md                  # Check single file
  %(prog)s docs/                      # Check all .md files in directory
  %(prog)s . --timeout 15              # Custom timeout
  %(prog)s docs/ --ignore "twitter.com,linkedin.com"  # Skip domains
        """
    )
    parser.add_argument('path', help='File or directory to scan for markdown files')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')
    parser.add_argument('--ignore', type=str, default='', help='Comma-separated domains to skip')
    parser.add_argument('--workers', type=int, default=5, help='Number of concurrent workers (default: 5)')
    
    args = parser.parse_args()
    target = Path(args.path)
    ignore_domains = [d.strip().lower() for d in args.ignore.split(',') if d.strip()]
    
    if not target.exists():
        print(f'❌ Path not found: {target}')
        sys.exit(1)
    
    # Find markdown files
    md_files = find_markdown_files(target)
    if not md_files:
        print(f'❌ No markdown files found in: {target}')
        sys.exit(1)
    
    print(f'🔍 Scanning {len(md_files)} markdown file(s)...\n')
    
    # Collect all links by file
    file_links: Dict[str, List[Tuple[str, str]]] = {}
    all_links: List[Tuple[str, str, str]] = []  # (file, text, url)
    total_links = 0
    
    for md_file in md_files:
        content = md_file.read_text(encoding='utf-8', errors='replace')
        links = extract_links(content)
        filtered = [(t, u) for t, u in links if not should_ignore(u, ignore_domains)]
        if filtered:
            rel_path = str(md_file.relative_to(target.parent if target.is_file() else target))
            file_links[rel_path] = filtered
            for text, url in filtered:
                all_links.append((rel_path, text, url))
            total_links += len(filtered)
    
    if total_links == 0:
        print('✅ No HTTP links found.')
        sys.exit(0)
    
    print(f'📎 Found {total_links} unique link(s) to check...\n')
    
    # Check links concurrently
    unique_urls = list(dict.fromkeys(u for _, _, u in all_links))
    url_results: Dict[str, Tuple[Optional[int], str]] = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(check_link, url, args.timeout): url for url in unique_urls}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            url, status, error = future.result()
            url_results[url] = (status, error)
            done += 1
            if done % 10 == 0 or done == len(unique_urls):
                print(f'\r  Progress: {done}/{len(unique_urls)}', end='', flush=True)
    
    print('\n')
    
    # Report results
    ok_count = 0
    broken_count = 0
    redirect_count = 0
    
    broken_by_file: dict[str, list[dict]] = defaultdict(list)
    
    for file, text, url in all_links:
        status, error = url_results.get(url, (None, 'Not checked'))
        if status and 200 <= status < 300:
            ok_count += 1
        elif status and 300 <= status < 400:
            redirect_count += 1
            broken_by_file[file].append({
                'text': text, 'url': url, 'status': status, 'error': f'Redirect {status}'
            })
        else:
            broken_count += 1
            broken_by_file[file].append({
                'text': text, 'url': url, 'status': status, 'error': error or f'Status {status}'
            })
    
    # Summary
    print('=' * 60)
    print(f'  ✅ OK:        {ok_count}')
    print(f'  ⚠️  Redirects:  {redirect_count}')
    print(f'  ❌ Broken:     {broken_count}')
    print('=' * 60)
    
    if broken_by_file:
        print(f'\n{"=" * 60}')
        print('  BROKEN LINKS REPORT')
        print(f'{"=" * 60}\n')
        for file, issues in broken_by_file.items():
            print(f'📄 {file}')
            for issue in issues:
                text = issue['text'][:50] + '...' if len(issue['text']) > 50 else issue['text']
                print(f'   [{issue["status"] or "ERR"}] {issue["url"]}')
                if text:
                    print(f'         Text: "{text}"')
                if issue['error']:
                    print(f'         Error: {issue["error"]}')
            print()
    
    sys.exit(1 if broken_count > 0 else 0)


if __name__ == '__main__':
    main()
