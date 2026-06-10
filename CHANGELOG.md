# Changelog

## [1.1.0] — setup.ps1 + Notifications

**Added:**
- `scripts/setup.ps1` — idempotent one-command setup:
  - Checks prerequisites (Python, winget, NVIDIA GPU)
  - Installs Ollama via winget if missing
  - Pulls 3 models (llama3.2, deepseek-coder-v2:lite, nomic-embed-text)
  - Creates Python venv at `~/.local-ai-stack/venv`
  - Installs deps via `pip install -e .`
  - Copies `.env.example` → `.env` if not exists
  - Creates data directories (logs, reports, catalogs, backups)
  - Sets `OLLAMA_KEEP_ALIVE=0` (zero-idle)
  - Optional `-ScheduleTasks` flag for Windows Task Scheduler
  - Runs `vls doctor` to verify
- `vls doctor` now sends Windows toast on warnings/fails
- `vls doctor` optionally sends email (if SMTP configured in `.env`)

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
