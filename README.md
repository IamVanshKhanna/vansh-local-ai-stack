# vansh-local-ai-stack

Local AI toolkit for Windows — file management, system monitoring, and document search. All powered by AI running on your laptop. No cloud, no API keys, no monthly fees.

```
vls doctor   →  System health check
vls report   →  Disk usage report
vls scan     →  Scan folders and build a file catalog
vls classify →  Sort files by type
vls generate →  Generate reorganization plans
vls apply    →  Execute file moves (dry-run by default)
vls index    →  Index documents for search
vls query    →  Ask questions about your documents
```

## Quick Start

```powershell
.\setup.ps1
```

One command — installs Ollama, downloads 3 AI models, creates environment, verifies.

## Resource Profile

| State | RAM | GPU | CPU |
|-------|-----|-----|-----|
| Idle | ~50 MB | 0% | 0% |
| Active (inference) | 2–6 GB | 2–6 GB VRAM | varies |
| Automation scripts | ~20 MB transient | 0% | brief |

Models unload when not in use (`OLLAMA_KEEP_ALIVE=0`).

## Documentation

- [GETTING_STARTED.md](GETTING_STARTED.md) — Plain-language guide for all users
- [SETUP.md](SETUP.md) — Detailed setup and scheduled tasks
- [CHANGELOG.md](CHANGELOG.md) — Version history

## License

MIT
