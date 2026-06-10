# Changelog

## [1.0.0] — Scenario B Baseline

**Breaking changes from 0.1.0:**
- Repo stripped to B essentials (~60 files → ~35)
- All 10 docs/ and n8n config removed (superseded by SETUP.md)
- `pyproject.toml` backend fixed to `setuptools.build_meta`
- Dependencies trimmed to B core (removed langchain, chromadb, docx, lxml)
- CI now runs Windows + Ubuntu matrix on Python 3.11 + 3.12
- GPU check rewritten for NVIDIA (was stubbed for AMD)
- Added `vls doctor` — one-command system health summary
- Added `setup.ps1` — single-script setup automation
- `scripts/requirements.txt` merged into top-level
- `__pycache__` removed from git tracking
- Placeholder npm files removed
- `.bolt/` config removed

## Planned

### [1.1.0]
- setup.ps1: fully idempotent, auto-imports scheduled tasks
- vls doctor: notification support (toast + email)

### [1.2.0]
- Windows Task Scheduler .xml exports
- Automated daily health check, weekly disk report, monthly backup

### [1.3.0]
- Notification hooks (Windows toast, optional email)
