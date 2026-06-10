# Changelog

## [2.0.0] — UX Overhaul: Menu, Organize, Report, Ask (2026-06-11)

**Added:**
- `vls` (no args) — interactive numbered menu (press 1-5, no commands to remember)
- `vls organize <folder>` — one-command file cleanup (scan→classify→plan→apply in one step)
- `vls --ask "what you want"` — natural language mode (type English, LLM interprets and runs the right command)
- Better `vls report` — shows visual usage bars, temp file count/size, largest files in Temp and Downloads
- Better `vls index` — validates paths exist before indexing, clearer error messages

**Changed:**
- `vls.py`: major UX overhaul — menu system, organize orchestrator, ask interpreter, improved report
- `pyproject.toml`: version bumped to 2.0.0

**Removed:**
- The old 4-step pipeline (scan→classify→generate→apply) still works but is superseded by `vls organize`

**How to use:**
- Just type `vls` and press Enter → menu appears
- `vls organize ~/Downloads` → categorize and organize your Downloads folder
- `vls --ask "how full is my disk"` → plain English query
- All old commands still work (`vls doctor`, `vls index`, `vls query`, etc.)

## [1.4.0] — PDF, DOCX & Image RAG (2026-06-11)

**Added:**
- `scripts/extract_text.py` — unified text extraction dispatcher:
  - `extract_pdf(path)` — text extraction via `pypdf`
  - `extract_docx(path)` — paragraph extraction via `python-docx`
  - `extract_image(path)` — OCR via `pytesseract` + `Pillow` (supports HEIC/HEIF iPhone format via `pillow-heif`)
  - `extract_file(path)` → returns `(content, file_type)` dispatcher
- `vls index` now supports PDF (`.pdf`), DOCX (`.docx`), and images (`.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.webp`, `.heic`, `.heif`)
- `file_type` column in `documents` table — tracks "text", "pdf", "docx", or "image"
- Automatic Tesseract detection on Windows (common install paths)
- Schema migration: adds `file_type` column to existing databases gracefully
- 23 new tests covering all extraction paths, dispatch logic, error handling, and edge cases

**Changed:**
- `pyproject.toml`: version bumped to 1.4.0, 5 new dependencies (`pypdf`, `python-docx`, `pillow`, `pytesseract`, `pillow-heif`)
- `scripts/setup.ps1`: installs Tesseract via winget (`UB-Mannheim.TesseractOCR`); caches model pull status (skips already-pulled models)
- `scripts/index_docs.py`: `is_text_file()` → `is_indexable()`, `read_file()` → `extract_file()` dispatch
- `tests/test_rag.py`: updated imports and assertions for renamed functions

**Dependencies (new):**
- `pypdf>=3.0.0`, `python-docx>=0.8.11`, `pillow>=9.0.0`, `pytesseract>=0.3.10`, `pillow-heif>=0.7.0`
- System: Tesseract OCR installed via `winget install UB-Mannheim.TesseractOCR`

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

## [1.3.1] — UX Fixes (2026-06-10)

**Fixed:**
- `vls apply --force` now auto-creates missing destination directories
  (previously skipped files with "destination directory does not exist")
- `setup.ps1 -ScheduleTasks` no longer shows misleading admin warning
  (env var expansion made admin unnecessary)
- `vls apply --help` now documents `--force` behaviour

## [1.2.1] — Bug Fixes (2026-06-10)

**Fixed:**
- `vls.py` report command: wrong dict keys (`free`/`total` → `free_gb`/`total_gb`),
  also removed double GB-to-bytes conversion
- `scripts/setup.ps1`: added `ExpandEnvironmentVariables()` call on XML
  before `schtasks /create` to resolve `%USERDOMAIN%\%USERNAME%` at runtime

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

## [2.2.0] — Dashboard UX Overhaul + Resource Monitor Fix (2026-06-11)

**Added:**
- Web dashboard (`vls dashboard --port 8080`): dark-theme single-page UI with live system monitoring
- Resource monitor (`/api/resources`): CPU/RAM/GPU bars with color thresholds, top 10 processes, Ollama model memory
- Health check (`/api/doctor`): Ollama, GPU, RAM, Disk, Scripts — all pass/fail at a glance
- Disk report (`/api/report`): drive usage bars, temp file analysis, largest files
- Scope-aware search: dropdown for All/C:/D:/Browse, index status badges per drive
- Folder-aware organize: `detect_existing_clusters()` — preserves subfolder structure, checkbox UI
- Button debounce + spinners: `wrap()` async guard disables all buttons during actions, shows spinner
- Toast notifications, live connection indicator (pulsing dot), "last refreshed" timestamp
- GPU VRAM bar (separate from util bar), zebra-striped process list, card hover effects
- Connection retry — click status badge when connection lost
- `vls.py`: dashboard subcommand with `--port` flag

**Changed:**
- `resource_monitor.py`: 10s GPU cache prevents nvidia-smi from blocking `/api/resources`; CPU interval fallback for accurate measurement
- `dashboard.py`: 12 API routes, cache-busting headers, mobile responsive (768px breakpoint)
- `rag_dal.py`: added `get_all_documents()`, `path_prefix` filter in `get_all_chunks()`/`search_similar()`
- `rag_query.py`: `scope` param for path-prefix filtering
- `generate_plan.py`: new `detect_existing_clusters()` function
- `pyproject.toml`: version bumped to 2.2.0

**Added (tests):**
- `tests/test_organize_preserve.py`: 6 new tests for `detect_existing_clusters` — 144 total

**Model Council rating:** 9.1/10 — Approved.

## [2.3.0] — Hostname Dashboard + GPU VRAM Fix + CPU Smoothing (2026-06-11)

**Added:**
- Dynamic dashboard title: shows device hostname (e.g. "MR_STRANGER Dashboard") instead of "Hermes Dashboard"
- GPU temperature (`temperature.gpu`) and power draw (`power.draw`) in nvidia-smi query — displayed in GPU card sub-text
- System uptime in header-right (e.g. "Uptime: 2h 15m") with days/hours/minutes breakdown
- Refresh rate selector: dropdown in header (1s / 3s / 5s / 10s / Paused)
- Keyboard shortcuts: `D`=Doctor `R`=Report `O`=Organize `S`=Search `I`=Index `?`=help overlay
- Tab visibility pause: switches to 10s when tab hidden, resumes user rate when visible
- Undo organize button + `/api/undo-organize` endpoint with `reverse_moves()` safety net
- `/api/smart-targets` endpoint: suggests organize targets from existing file locations
- `/api/drives` + `/api/browse` endpoints: drive listing and directory browsing for search scope
- Browse UI in search scope: shows drive buttons, clickable directories, path input
- `suggest_targets_from_data()` in `generate_plan.py` — smart cross-drive target suggestions

**Changed:**
- GPU card: VRAM % is now the primary bar metric (was GPU util which stays at 0% idle); util + temp + power + VRAM shown in sub-text line
- All resource cards now have **uniform height** — removed `extra` param and `rc-gpu-mem` div; VRAM info moved into `rc-sub` line
- CPU smoothing: 3-point rolling average (`_cpu_history`) replaces interval-0.0 fallback — no more 19-point jumps between 3s polls
- Search results: now show full file path (`s.path`) instead of just file name
- Clean UI: stripped all instructional text from organize/index/search panels (just controls, no guidance)
- `dashboard.py`: imports `socket` for dynamic hostname, stores `_last_moves` for undo safety
- `apply_moves.py`: new `reverse_moves()` function swaps source/destination
- `resource_monitor.py`: nvidia-smi queries `temperature.gpu` and `power.draw`; `_cpu_history` module-level list for smoothing; `uptime` in return dict

**Added (tests):**
- (all 144 existing tests pass unchanged; no regressions)

**Model Council rating:** pending — target 9.85/10

## Planned
