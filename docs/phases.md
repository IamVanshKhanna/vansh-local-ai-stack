# Implementation Phases

This document outlines the phased approach to building the local AI stack, ensuring each phase delivers value before expanding scope.

## Phase 0: Foundation (Current)

**Goal**: Working Ollama + Continue + Jan setup

**Duration**: 1-2 days

### Checklist

- [ ] Install Ollama
  - [ ] Download from ollama.com
  - [ ] Verify `ollama --version`
  - [ ] Test `ollama run llama3.2`

- [ ] Install Continue
  - [ ] VS Code extension installed
  - [ ] Config points to localhost:11434
  - [ ] Autocomplete working
  - [ ] Chat sidebar functional

- [ ] Install Jan
  - [ ] Desktop app installed
  - [ ] Connected to Ollama
  - [ ] Conversation saved locally

- [ ] Pull Initial Models
  - [ ] `llama3.2` for general use
  - [ ] `deepseek-coder-v2:lite` for coding
  - [ ] `nomic-embed-text` for future RAG

### Success Criteria

- Can ask coding questions in VS Code via Continue
- Can have conversations in Jan
- Both use local Ollama, no external API calls
- Startup time < 30 seconds

---

## Phase 1: Automation Scripts

**Goal**: Practical Python automation running on schedule

**Duration**: 1 weekend

### Scripts to Build

#### 1. `scan_drives.py`

**Purpose**: Catalog filesystem for analysis

**Features**:
- Scan specified directories
- Record path, size, extension, modified date
- Output to JSON/SQLite
- Handle permission errors gracefully

**Usage**:
```bash
python scripts/scan_drives.py --paths "D:\,E:\" --output catalog.json
```

#### 2. `classify_files.py`

**Purpose**: Intelligently categorize files

**Features**:
- Rule-based classification by extension/path
- Optional LLM-assisted classification for ambiguous files
- Categories: Documents, Media, Code, Archives, etc.

**Usage**:
```bash
python scripts/classify_files.py --input catalog.json --rules config/rules.yaml
```

#### 3. `apply_moves.py`

**Purpose**: Execute file reorganization safely

**Features**:
- Dry-run mode by default
- Create move plan, review, execute
- Handle conflicts (same name)
- Log all operations

**Usage**:
```bash
python scripts/apply_moves.py --plan moves.json --dry-run
python scripts/apply_moves.py --plan moves.json --execute
```

#### 4. `disk_report.py`

**Purpose**: Storage analysis and alerts

**Features**:
- Drive space summary
- Largest files/folders
- Duplicate detection (optional)
- Email/notification output

**Usage**:
```bash
python scripts/disk_report.py --drives "C,D,E" --threshold 90
```

#### 5. `health_check.py`

**Purpose**: System health monitoring

**Features**:
- Ollama availability check
- GPU status
- RAM usage
- Disk space warnings
- Output status as JSON

**Usage**:
```bash
python scripts/health_check.py --output status.json
```

### Task Scheduler Setup

Wire each script into Windows Task Scheduler:
- Disk report: Weekly
- Health check: Daily
- File scan: Monthly (or on demand)
- Classification: After scan

See [scheduler-notes.md](../config/scheduler-notes.md) for detailed setup.

### Success Criteria

- All scripts run without errors
- At least one script on scheduled run
- Output logs accessible in `~/.local-ai-stack/logs/`
- Reports visible and actionable

---

## Phase 2: RAG Pipeline

**Goal**: Local document search with context

**Duration**: 1-2 weekends

### Components

#### Vector Database

- **ChromaDB** or **Qdrant** (local mode)
- Embedded in Python or separate Docker container
- Persistent storage in `~/.local-ai-stack/vector-db/`

#### Embedding Pipeline

```
Documents (PDF, TXT, MD, DOCX)
    │
    ▼
Chunking (512-1024 tokens)
    │
    ▼
Embedding via nomic-embed-text (Ollama)
    │
    ▼
Storage in Vector DB
```

#### Query Interface

- Command-line tool for initial testing
- Integration into Jan/Open WebUI later
- Context injection for LLM queries

### Use Cases

- Search through personal notes
- Query technical documentation
- Find relevant code snippets
- Semantic search across PDFs

### Success Criteria

- Index > 100 documents
- Query response < 5 seconds
- Relevant results in top 5
- All processing local

---

## Phase 3: Advanced Chat UI

**Goal**: Feature-rich web interface

**Duration**: 1-2 weekends

### Option A: Open WebUI

**Pros**:
- User accounts (if needed)
- RAG integration built-in
- Model management
- Prompt templates

**Cons**:
- Docker required
- Higher resource usage

### Option B: Enhanced Jan

**Pros**:
- Already installed
- Desktop app simplicity
- Lower resource usage

**Cons**:
- Limited RAG support
- Fewer features

### Implementation

1. Install Docker Desktop (for Open WebUI)
2. Run Open WebUI container
3. Connect to Ollama
4. Configure RAG if using
5. Import chat history from Jan (optional)

### Success Criteria

- Web UI accessible at localhost:8080
- Multiple model selection
- Chat history preserved
- Document upload working

---

## Phase 4: Workflow Automation

**Goal**: n8n for complex automation

**Duration**: Ongoing

### Use Cases

- Email to task conversion
- File processing pipelines
- API integrations (optional cloud)
- Scheduled multi-step workflows

### Setup

1. Install n8n via npm or Docker
2. Create initial workflows
3. Connect to local scripts
4. Schedule via n8n internal scheduler

See [n8n-setup-notes.md](../config/n8n-setup-notes.md) for details.

### Success Criteria

- n8n running locally
- ≥ 1 useful workflow
- Scheduled execution working
- Logs accessible

---

## Phase 5: Voice Input

**Goal**: Speech-to-text for queries

**Duration**: 1 weekend

### Implementation

1. Install Whisper (OpenAI or faster-whisper)
2. Create audio capture script
3. Transcribe and send to LLM
4. Optional: TTS for response

### Options

- **OpenAI Whisper** (local): Accurate, slower
- **faster-whisper**: Faster, GPU-accelerated
- **Ollama Whisper**: Simpler, single backend

### Success Criteria

- Voice recording captured
- Transcription accuracy > 90%
- Integration with chat interface

---

## Phase 6: Agents

**Goal**: Autonomous task execution

**Duration**: Ongoing research

### Patterns

- Hermes-style tool calling
- ReAct (Reasoning + Acting)
- Multi-step planning

### Tools Integration

- File operations
- Web search (optional)
- Code execution (sandboxed)
- Database queries

### Success Criteria

- Agent can complete 3+ step tasks
- Safe boundaries enforced
- Execution logged

---

## Phase 7: Hybrid Cloud (Optional)

**Goal**: Selective cloud integration

**Duration**: As needed

### Use Cases

- Offload heavy queries to cloud API
- Sync state across devices
- Phone control from laptop

### Implementation

- Conditional API fallback
- Sync service (Syncthing or cloud)
- Tailscale for secure access

### Success Criteria

- Fallback works when local fails
- Data synced securely
- Remote access functional

---

## Prioritization

| Phase | Value | Effort | Priority |
|-------|-------|--------|----------|
| 0 | High | Low | **DO FIRST** |
| 1 | High | Medium | **DO NEXT** |
| 2 | High | Medium | After Phase 1 |
| 3 | Medium | Low | Quick win |
| 4 | Medium | Medium | As needed |
| 5 | Medium | Medium | Quality of life |
| 6 | High | High | Research phase |
| 7 | Low | Variable | Optional |

## Getting Started

Start with [Phase 0](#phase-0-foundation-current) and ensure you have a working Ollama setup before building automation or RAG.

Next: [Model Selection Guide](models.md)
