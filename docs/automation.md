# Automation Guide

This document describes automation patterns, script conventions, and integration points for the local AI stack.

## Overview

Automation in this stack serves three purposes:

1. **System maintenance** - Disk reports, health checks, backups
2. **File management** - Organization, classification, cleanup
3. **Data pipelines** - Processing, transformation, indexing (future RAG)

---

## Script Conventions

### Directory Structure

```
scripts/
├── scan_drives.py       # Scan filesystem
├── classify_files.py    # Categorize files
├── apply_moves.py       # Execute file moves
├── disk_report.py       # Storage reports
├── health_check.py      # System monitoring
└── examples/
    ├── notify.py        # Notification helper
    └── logger.py        # Logging utilities
```

### Standard Arguments

All scripts follow consistent argument patterns:

```python
import argparse

parser = argparse.ArgumentParser(description="Script description")
parser.add_argument("--output", "-o", help="Output file path")
parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
parser.add_argument("--config", help="Path to config file")
```

### Logging

Use structured logging for consistency:

```python
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use
logger.info("Starting scan")
logger.warning("Permission denied: /path/to/file")
logger.error("Failed to connect to Ollama")
```

### Configuration

Scripts read from:
1. Command-line arguments (highest priority)
2. Environment variables
3. Config files (YAML/JSON)
4. Defaults

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
```

### Error Handling

Scripts should:
- Handle expected errors gracefully
- Exit with non-zero codes on failure
- Write errors to stderr
- Log details for debugging

```python
import sys

try:
    result = risky_operation()
except PermissionError as e:
    logger.error(f"Permission denied: {e}")
    sys.exit(1)
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    sys.exit(2)
```

---

## Core Scripts

### 1. scan_drives.py

**Purpose**: Catalog filesystem for analysis

**Workflow**:
```
Input: List of paths to scan
Process: Walk directories, collect metadata
Output: JSON/SQLite catalog
```

**Key Features**:
- Walk directories recursively
- Record: path, size, extension, timestamps, hash (optional)
- Handle permission errors
- Skip system directories by default
- Progress indicator for large scans

**Integration Points**:
- Output feeds into `classify_files.py`
- Can trigger on-demand or scheduled
- Results stored in `~/.local-ai-stack/catalogs/`

---

### 2. classify_files.py

**Purpose**: Categorize files based on rules and LLM

**Workflow**:
```
Input: Catalog from scan_drives.py
Process: Apply classification rules
  1. Extension-based (fast, deterministic)
  2. Path-based (e.g., project folders)
  3. LLM-assisted (ambiguous files)
Output: Classification map
```

**Classification Rules**:

| Category | Extensions | Path Patterns |
|----------|------------|---------------|
| Documents | pdf, docx, txt, md | /Documents/ |
| Media | mp4, mkv, mp3, jpg | /Videos/, /Music/ |
| Code | py, js, ts, json | /projects/ |
| Archives | zip, rar, 7z | /Downloads/ |
| Backups | bak, old | /backups/ |
| System | dll, exe, sys | /Windows/, /Program Files/ |

**LLM Classification** (for ambiguous files):
```python
def classify_with_llm(filename: str, llm_client) -> str:
    prompt = f"Classify this file into one category: {filename}"
    response = llm_client.generate(prompt)
    return parse_category(response)
```

---

### 3. apply_moves.py

**Purpose**: Execute file reorganization safely

**Safety First**:
- **Always dry-run first**
- Create move plan
- Verify no conflicts
- Log all operations
- Support rollback

**Workflow**:
```
Input: Classification map + target structure
Process:
  1. Generate move operations
  2. Validate (dest exists, no overwrite without flag)
  3. Dry-run: print plan, exit
  4. Execute: copy, verify, delete source
Output: Execution log + new locations
```

**Move Plan Format**:
```json
{
  "moves": [
    {
      "source": "/Downloads/report.pdf",
      "destination": "/Documents/2024/report.pdf",
      "size": 1024000,
      "operation": "move"
    }
  ]
}
```

---

### 4. disk_report.py

**Purpose**: Generate storage analysis

**Metrics**:
- Total/free space per drive
- Largest files
- Largest directories
- File type distribution
- Duplicate detection (optional)

**Output Formats**:
- JSON (machine-readable)
- Markdown (human-readable)
- Email (scheduled reports)

**Alert Thresholds**:
```python
# Alert if drive > 90% full
if used_percent > 90:
    send_alert(f"Drive {drive} at {used_percent}% capacity")
```

---

### 5. health_check.py

**Purpose**: Monitor system health

**Checks**:

| Component | Check | Pass Condition |
|-----------|-------|----------------|
| Ollama | HTTP request to localhost:11434 | 200 response |
| GPU | Driver query | Detected |
| RAM | Memory usage | < 90% |
| Disk | Free space | > 10 GB |
| Scripts | Last run time | Within expected window |

**Output**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "ollama": {"status": "pass", "latency_ms": 12},
    "gpu": {"status": "pass", "vram_used_gb": 2.1},
    "ram": {"status": "pass", "used_percent": 65},
    "disk": {"status": "pass", "free_gb": 150}
  }
}
```

---

## LLM Integration

### Calling Ollama from Python

```python
import requests

def query_ollama(prompt: str, model: str = "llama3.2") -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False
        }
    )
    return response.json()["response"]

# Example: classify a file
category = query_ollama(
    "Classify this filename into one word: 'backup_project_v2.zip'"
)
# Output: "backup"
```

### Async Batching

For multiple queries:

```python
import asyncio
import aiohttp

async def batch_classify(filenames: list[str]) -> list[str]:
    async with aiohttp.ClientSession() as session:
        tasks = [
            query_ollama_async(session, f"Category for: {f}")
            for f in filenames
        ]
        return await asyncio.gather(*tasks)
```

---

## Windows Task Scheduler

### Basic Setup

1. Open Task Scheduler
2. Create Task (not Basic Task for more control)
3. Configure:
   - **General**: Run as your user, run whether logged in or not
   - **Triggers**: Schedule (daily, weekly, etc.)
   - **Actions**: Start Program (python.exe path, script path)
   - **Conditions**: Start only if on AC power (optional)

### Script as Scheduled Task

```
Program: C:\Python311\python.exe
Arguments: C:\scripts\disk_report.py --output C:\logs\disk_report.json
Start in: C:\scripts
```

### Logging Output

```powershell
# In Arguments, redirect output:
python C:\scripts\disk_report.py >> C:\logs\disk_report.log 2>&1
```

See [scheduler-notes.md](../config/scheduler-notes.md) for detailed examples.

---

## Example Workflow: Monthly File Organization

```
Day 1, 2:00 AM
    │
    ├─► Task 1: scan_drives.py --paths "D:\,E:\" --output monthly_scan.json
    │
    ▼
Day 1, 3:00 AM
    │
    ├─► Task 2: classify_files.py --input monthly_scan.json --rules rules.yaml
    │
    ▼
Day 1, 4:00 AM (Manual review day)
    │
    ├─► User reviews classification
    │   └─► Edits or approves move plan
    │
    ▼
Day 2, 2:00 AM
    │
    └─► Task 3: apply_moves.py --plan approved_moves.json --execute
```

---

## Error Recovery

### Script Failure

```
Script fails → Exit code != 0 → Task Scheduler logs error
                               │
                               └─► Retry logic in Task Scheduler (optional)
                               └─► Manual intervention via health_check.py
```

### Ollama Unavailable

Scripts that need LLM should:
1. Check Ollama availability first
2. Fallback to rule-based processing if down
3. Log the fallback event

```python
def classify_safe(filename: str) -> str:
    try:
        return classify_with_llm(filename)
    except requests.ConnectionError:
        logger.warning("Ollama unavailable, using rule-based classification")
        return classify_by_extension(filename)
```

---

## Future Integration

### n8n Workflows

Scripts can be called from n8n:
- Execute node: Run Python script
- Webhook trigger: Script exposes HTTP endpoint
- Schedule node: Replace Task Scheduler

### RAG Pipeline

```python
def update_rag_index(new_files: list[str]):
    # 1. Read documents
    # 2. Generate embeddings (nomic-embed-text)
    # 3. Update vector database
    pass
```

---

## Security Considerations

- Scripts run with user permissions
- Never expose Ollama API externally
- Validate file paths (no traversal)
- Sanitize inputs before LLM
- Log sensitive operations (but not sensitive data)

---

## Example Scenarios

### Scenario 1: Weekly Drive Cleanup

**Goal**: Keep Downloads and temp folders tidy every Sunday.

```bash
# Step 1: Scan the messy directories
python scripts/scan_drives.py --paths "D:\Downloads,D:\Temp" --output weekly_scan.json

# Step 2: Classify what's in there
python scripts/classify_files.py --input weekly_scan.json --output classified.json --use-llm

# Step 3: Review the classification
# Open classified.json, check category assignments.
# Create a move plan manually or generate one from categories.

# Step 4: Generate move plan (example target structure)
# target_structure.json:
# {
#   "documents": "D:\\Organized\\Documents",
#   "media": "D:\\Organized\\Media",
#   "code": "D:\\Organized\\Code",
#   "archives": "D:\\Organized\\Archives",
#   "executables": "D:\\Organized\\Installers"
# }

# Step 5: Dry-run the moves
python scripts/apply_moves.py --plan moves.json --dry-run

# Step 6: Review output, then execute
python scripts/apply_moves.py --plan moves.json --execute

# Step 7: Report results
python scripts/disk_report.py --drives "D" --format markdown --output weekly_report.md
```

**Schedule with Task Scheduler**: Run Steps 1-2 on Sunday 2 AM, Steps 5-6 after manual review.

---

### Scenario 2: Gmail Triage via n8n

**Goal**: Summarize daily emails and flag action items.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Gmail Node  │────►│  Ollama Node │────►│  Notion /    │
│  (Trigger:   │     │  (Summarize  │     │  Todoist     │
│  new email)  │     │  + classify) │     │  (Action     │
│              │     │              │     │   items)     │
└──────────────┘     └──────────────┘     └──────────────┘
```

**n8n Workflow Steps**:

1. **Gmail Trigger**: Poll for new emails (every 30 min)
2. **Function Node**: Extract subject, sender, body
3. **HTTP Request Node → Ollama**:
   ```
   POST http://localhost:11434/api/generate
   Prompt: "Summarize this email and list action items: {subject}\n{body}"
   Model: llama3.2
   ```
4. **If Node**: Check if action items exist
5. **Todoist Node** (or Notion): Create task for each action item
6. **Email Node**: Send daily digest at 6 PM

**No Python script required** — this is entirely within n8n. But you can add a health check:

```bash
# Verify Ollama is up before n8n workflow runs
python scripts/health_check.py --only ollama
```

---

### Scenario 3: New Project Setup

**Goal**: When starting a new coding project, scaffold the folder and configure Continue.

```bash
# Step 1: Check system health before starting
python scripts/health_check.py --only ollama,gpu,ram --output project_setup_health.json

# Step 2: Create project directory structure
# (Manual or use a template script)

# Step 3: Verify disk space for the new project
python scripts/disk_report.py --drives "D" --format text

# Step 4: Configure Continue for the project
# Add .continue/config.json in the project root:
# {
#   "models": [{"title": "Ollama", "provider": "ollama", "model": "deepseek-coder-v2:lite"}],
#   "contextProviders": [{"name": "code"}]
# }

# Step 5: Start coding with AI assistance in VS Code
```

This scenario uses `health_check.py` and `disk_report.py` as pre-flight checks before starting work, ensuring Ollama is running and disk space is sufficient.

---

## Testing Scripts

### tests/ Directory

```
tests/
├── test_scan_drives.py    # Unit tests for scan_drives
├── test_classify_files.py # Unit tests for classification
├── test_apply_moves.py    # Unit tests for move operations
├── test_disk_report.py    # Unit tests for disk reports
├── test_health_check.py   # Unit tests for health checks
└── README.md              # How to run tests
```

### Sample Invocations

Each script supports `--help` for full usage. Below are quick-test commands that can be run immediately.

#### scan_drives.py

```bash
# Scan a single small directory (safe, read-only)
python scripts/scan_drives.py --paths "/tmp" --output /tmp/test_catalog.json --verbose

# Verify output
cat /tmp/test_catalog.json | python -m json.tool | head -20

# Scan with SQLite output
python scripts/scan_drives.py --paths "/tmp" --output /tmp/test_catalog.db --format sqlite

# View SQLite results
sqlite3 /tmp/test_catalog.db "SELECT COUNT(*) FROM files;"
```

#### classify_files.py

```bash
# Classify from catalog (rule-based only, no LLM needed)
python scripts/classify_files.py --input /tmp/test_catalog.json --output /tmp/test_classified.json

# With LLM classification (requires Ollama running)
python scripts/classify_files.py --input /tmp/test_catalog.json --output /tmp/test_classified.json --use-llm --model llama3.2

# Verify output
cat /tmp/test_classified.json | python -m json.tool | grep '"category"'
```

#### apply_moves.py

```bash
# Always test with dry-run first (default behavior)
python scripts/apply_moves.py --plan test_moves.json --dry-run --verbose

# Create a test move plan first:
echo '{"moves":[{"source":"/tmp/test_file.txt","destination":"/tmp/organized/test_file.txt","size":100,"category":"test"}]}' > /tmp/test_moves.json
touch /tmp/test_file.txt

# Dry-run
python scripts/apply_moves.py --plan /tmp/test_moves.json --dry-run

# Execute (after reviewing dry-run output)
python scripts/apply_moves.py --plan /tmp/test_moves.json --execute --output /tmp/move_log.json
```

#### disk_report.py

```bash
# Quick report for current drive
python scripts/disk_report.py --drives "/" --format json

# Markdown report to file
python scripts/disk_report.py --drives "/" --format markdown --output /tmp/test_report.md

# With large file listing
python scripts/disk_report.py --drives "/" --include-large-files --large-file-count 5

# Alert mode (exits with error if drive > threshold)
python scripts/disk_report.py --drives "/" --threshold 90 --alert
```

#### health_check.py

```bash
# Full health check
python scripts/health_check.py --check-all

# Check only Ollama availability
python scripts/health_check.py --only ollama

# Check Ollama and RAM
python scripts/health_check.py --only ollama,ram

# Save results to file
python scripts/health_check.py --check-all --output /tmp/health.json

# Custom Ollama host
python scripts/health_check.py --only ollama --ollama-host http://localhost:11434
```

### Running Tests with pytest

```bash
# Install pytest
pip install pytest

# Run all tests
pytest tests/ -v

# Run a specific test
pytest tests/test_health_check.py -v

# Run with coverage
pytest tests/ -v --cov=scripts
```

---

## Next Steps

- [Phase Implementation](phases.md) - When to build which scripts
- [Scheduler Notes](../config/scheduler-notes.md) - Detailed Task Scheduler setup
- [RAG Setup](rag.md) - Future document indexing
- [Security and Backup Guide](security-and-backup.md) - Safety practices
