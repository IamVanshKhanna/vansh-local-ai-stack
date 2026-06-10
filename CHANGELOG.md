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

## [1.2.0] — Task Scheduler Automation

**Added:**
- `config/tasks/daily-health-check.xml` — runs `vls doctor` daily at 8am
- `config/tasks/weekly-disk-report.xml` — runs `vls report` Sundays at 9am
- `config/tasks/monthly-catalog-backup.xml` — backups catalog.db on 1st of month at 10am
- `setup.ps1 -ScheduleTasks`: admin check, auto-registers all 3 tasks via schtasks
- All task XMLs use `%USERPROFILE%` for portable paths (no hardcoded user)
- Tasks run on battery or AC, start if missed, 30-min timeout

## [1.3.0] — RAG Pipeline (2026-06-10)

**Added:**
- `vls index` — index text files for semantic search:
  - Reads .txt, .md, .py, .js, .ts, .json, .yaml, .csv, and 20+ text formats
  - Chunks content with configurable size/overlap (default 2048/256 chars)
  - Generates embeddings via Ollama (`nomic-embed-text`)
  - Stores in SQLite (`documents` + `chunks` tables with vector search)
- `vls query` — ask natural language questions about indexed documents:
  - Embeds query, finds top-k similar chunks via cosine similarity
  - Builds context prompt and answers via Ollama (`llama3.2`)
  - Shows source documents with relevance scores
- `scripts/db/schema_rag.sql` — new DB tables for documents and chunk embeddings
- `scripts/db/rag_dal.py` — DAL for RAG operations + pure-Python cosine similarity
- `scripts/index_docs.py` — document ingestion pipeline
- `scripts/rag_query.py` — retrieval-augmented generation query engine
- `config/.env.example` — added `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `RAG_TOP_K`
- 28 new tests covering docs, chunks, similarity search, chunking, embedding API, and CLI integration

**Changed:**
- No new pip dependencies — uses Ollama HTTP API for both embeddings and generation
- No Docker, no cloud, no always-running services

## [1.2.1] — Bug Fixes (2026-06-10)

**Fixed:**
- `vls.py` report command: wrong dict keys (`free`/`total` → `free_gb`/`total_gb`),
  also removed double GB-to-bytes conversion
- `scripts/setup.ps1`: added `ExpandEnvironmentVariables()` call on XML
  before `schtasks /create` to resolve `%USERDOMAIN%\%USERNAME%` at runtime

## [1.2.0] — Task Scheduler Automation

**Added:**
- `config/tasks/daily-health-check.xml` — runs `vls doctor` daily at 8am
- `config/tasks/weekly-disk-report.xml` — runs `vls report` Sundays at 9am
- `config/tasks/monthly-catalog-backup.xml` — backups catalog.db on 1st of month at 10am
- `setup.ps1 -ScheduleTasks`: admin check, auto-registers all 3 tasks via schtasks
- All task XMLs use `%USERPROFILE%` for portable paths (no hardcoded user)
- Tasks run on battery or AC, start if missed, 30-min timeout

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
