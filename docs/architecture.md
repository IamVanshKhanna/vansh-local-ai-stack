# Architecture Overview

This document describes the system design, component relationships, and data flow for the local AI stack.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        WINDOWS 11 LAPTOP                         │
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │              │      │              │      │              │  │
│  │   OLLAMA     │◄────►│   JAN /      │◄────►│  PYTHON      │  │
│  │   (Backend)  │      │   OPEN WEBUI │      │  SCRIPTS     │  │
│  │              │      │   (Chat UI)  │      │              │  │
│  └──────┬───────┘      └──────────────┘      └──────────────┘  │
│         │                                                        │
│         │ HTTP API (localhost:11434)                            │
│         │                                                        │
│  ┌──────▼───────┐                                                │
│  │              │                                                │
│  │   CONTINUE   │◄────► VS CODE                                 │
│  │  (Extension) │        (Editor)                                │
│  │              │                                                │
│  └──────────────┘                                                │
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │    MODELS    │      │   VECTOR     │      │  TASK        │  │
│  │  (GGUF)      │      │   DB (RAG)   │      │  SCHEDULER   │  │
│  │              │      │  (Future)    │      │              │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Ollama (Inference Engine)

**Role**: Single backend for all LLM inference

**Responsibilities**:
- Model serving and lifecycle management
- API endpoint for clients (Continue, Jan, scripts)
- GPU/CPU resource management
- Model quantization and optimization

**Configuration**:
```bash
# Default endpoint
OLLAMA_HOST=http://localhost:11434

# Model storage location
# Windows: C:\Users\<user>\.ollama\models
```

**Why Ollama?**
- Single binary, simple installation
- Automatic GPU detection
- Built-in model library
- RESTful API compatible with OpenAI SDK
- Supports custom GGUF models

### 2. Continue (Coding Client)

**Role**: AI assistant integrated into VS Code

**Responsibilities**:
- Context-aware code completion
- Multi-file understanding
- Custom instructions per project
- Chat interface for coding questions

**Configuration** (`~/.continue/config.json`):
```json
{
  "models": [
    {
      "title": "Ollama Llama",
      "provider": "ollama",
      "model": "llama3.2"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Ollama Autocomplete",
    "provider": "ollama",
    "model": "deepseek-coder-v2:lite"
  }
}
```

### 3. Jan / Open WebUI (Chat Interface)

**Role**: General-purpose ChatGPT-style interface

**Responsibilities**:
- Conversational AI access
- Chat history management
- Document upload and analysis
- Multiple model switching

**Comparison**:

| Feature | Jan | Open WebUI |
|---------|-----|------------|
| Installation | Desktop app | Docker container |
| Features | Basic + RAG | Advanced + auth |
| Resource usage | Lower | Higher |
| Best for | Quick start | Power users |

### 4. Python Scripts (Automation)

**Role**: File management, reports, health checks

**Responsibilities**:
- Scheduled filesystem operations
- Disk space monitoring
- Backup verification
- System health reporting

**Integration**: Windows Task Scheduler or Python `schedule` library

## Data Flow

### Coding Workflow

```
User types in VS Code
        │
        ▼
Continue extension captures context
        │
        ▼
Continue calls Ollama API
        │
        ▼
Ollama runs inference (GPU)
        │
        ▼
Response returned to Continue
        │
        ▼
Suggestion displayed in editor
```

### Chat Workflow

```
User sends message in Jan
        │
        ▼
Jan calls Ollama API
        │
        ▼
Ollama runs inference
        │
        ▼
Response streamed to Jan
        │
        ▼
Conversation updated
```

### Automation Workflow

```
Task Scheduler triggers script
        │
        ▼
Python script executes
(e.g., scan drives, classify files)
        │
        ▼
Script optionally calls Ollama
(for classification decisions)
        │
        ▼
Actions performed (move files, send report)
        │
        ▼
Log written to file/DB
```

## Resource Constraints

Given hardware (Ryzen 7 4800H, 32GB RAM, 6GB VRAM):

| Resource | Constraint | Strategy |
|----------|------------|----------|
| VRAM | 6 GB | Use 4-8B models, quantization |
| RAM | 32 GB | Limit model + app concurrency |
| CPU | 8 cores | Background tasks, not inference |

### Model Sizing Rules

- **GPU inference**: Models ≤ 5B parameters (4-bit) fit in VRAM
- **CPU fallback**: Larger models use system RAM (slower)
- **Recommendation**: llama3.2 (3B) on GPU, deepseek-coder-v2:lite on GPU

## Network Architecture

```
┌──────────────────────────────────────────────┐
│                 LOCALHOST                     │
│                                              │
│  Port 11434 ──► Ollama API (all clients)     │
│  Port 3000  ──► Jan (if web interface)      │
│  Port 8080  ──► Open WebUI (Docker)         │
│                                              │
│  NO EXTERNAL PORTS - All local traffic       │
└──────────────────────────────────────────────┘
```

**Security**: All services run on localhost only. No external network exposure.

## Future Components

### RAG Pipeline (Phase 2)

```
Documents ──► nomic-embed-text ──► Vector DB
                                              │
User query ─────────────────────────────────┼─► Retrieval
                                              │
                     Retrieved context ◄──────┘
                              │
                              ▼
                    Ollama generates response
```

### Agent Patterns (Phase 3)

```
User request ──► Agent (Hermes-style)
                     │
                     ├──► Tool: Query local files
                     ├──► Tool: Query RAG
                     ├──► Tool: Execute script
                     └──► Tool: Web search (optional)
```

## Failure Modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Ollama crash | Health check script | Auto-restart via Task Scheduler |
| GPU OOM | Ollama log | Fall back to CPU or smaller model |
| High RAM usage | System monitor | Kill non-essential processes |
| Script failure | Exit code + log | Alert via notification |

## Directory Layout

```
C:\Users\<user>\
├── .ollama\
│   └── models\           # Downloaded models
├── .continue\
│   └── config.json       # Continue configuration
├── AppData\Local\Jan\
│   └── data\             # Jan chat history
├── .local-ai-stack\
│   ├── logs\             # Script logs
│   ├── reports\          # Generated reports
│   ├── backups\          # Backup metadata
│   └── vector-db\        # Future RAG storage
└── vansh-local-ai-stack\
    └── scripts\          # This repository
```

## Security and Backups

All services run on localhost with no external exposure by default. Ollama has no built-in authentication, so binding to `127.0.0.1` is critical. The only script that modifies files (`apply_moves.py`) defaults to dry-run mode and requires `--execute` to make changes.

**Key practices**:
- Always run `classify_files.py` and `apply_moves.py` with `--dry-run` first; review output before executing
- Log every move operation to CSV/JSON and retain those logs for audit and recovery
- Enable BitLocker or folder encryption for sensitive data; never expose ports without auth and TLS
- Back up this repo (Git), config files, and RAG indexes weekly to an external SSD or encrypted cloud drive
- Double-check scheduled task paths — a typo can target the wrong directory

For the full guide, see [Security and Backup Guide](security-and-backup.md).

---

## Next Steps

- [Phase Implementation](phases.md) - What to build when
- [Model Selection](models.md) - Which models for which tasks
- [Automation Guide](automation.md) - Script patterns and examples
- [Security and Backup Guide](security-and-backup.md) - Security practices and backup strategy
