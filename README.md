# 🔗 Dead Link Checker

> Scan your markdown files for broken links — fast, simple, zero dependencies.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Sponsor](https://img.shields.io/badge/Sponsor-❤️-ff69b4)](https://github.com/sponsors/enzhen-x)

Dead Link Checker scans all `.md` files in a directory (or a single file) and checks every HTTP/HTTPS link — telling you which ones are **broken**, **redirected**, or **fine**.

## ✨ Why This Tool?

- **Zero dependencies** — uses only Python standard library
- **Fast** — concurrent checking (configurable workers)
- **Simple** — one command, readable output
- **CI-friendly** — non-zero exit code on broken links (great for GitHub Actions)

## 🚀 Quick Start

```bash
# Check a single file
python check_links.py README.md

# Check all markdown files in a directory (recursive)
python check_links.py docs/

# With custom timeout and ignore specific domains
python check_links.py . --timeout 15 --ignore "twitter.com,linkedin.com"

# High-concurrency mode (10 workers)
python check_links.py docs/ --workers 10
```

## 📋 Example Output

```
🔍 Scanning 12 markdown file(s)...

📎 Found 47 unique link(s) to check...

============================================================
  ✅ OK:        38
  ⚠️  Redirects:  3
  ❌ Broken:     6
============================================================

  BROKEN LINKS REPORT
============================================================

📄 docs/api.md
   [404] https://example.com/old-api
         Text: "deprecated API docs"
         Error: HTTP Error 404: Not Found

📄 README.md
   [ERR] https://dead-site.com
         Text: "getting started guide"
         Error: [Errno 8] nodename nor servname provided...
```

## 🔧 GitHub Actions Integration

```yaml
name: Check Links
on: [push, pull_request]
jobs:
  links:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Check dead links
        run: python check_links.py . --timeout 15
```

## 📦 Installation

No install needed! Just download `check_links.py` and run it:

```bash
curl -O https://raw.githubusercontent.com/enzhen-x/dead-link-checker/main/check_links.py
python check_links.py --help
```

Or clone the repo:

```bash
git clone https://github.com/enzhen-x/dead-link-checker.git
cd dead-link-checker
python check_links.py .
```

## 🎯 Use Cases

- **Documentation maintenance** — keep your docs links fresh
- **CI/CD pipelines** — fail builds when links break
- **Blog migration** — verify all external links still work
- **Open source projects** — automatically check README/CHANGELOG links

## 🤝 Contributing

Found a bug? Have an idea? PRs welcome!

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

💡 **Like this tool?** [Sponsor me on GitHub](https://github.com/sponsors/enzhen-x) to support more open-source utilities!
