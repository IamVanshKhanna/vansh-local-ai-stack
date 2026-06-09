# vansh-local-ai-stack

A lightweight, modular local AI workspace for coding, automation, and personal knowledge on a single Windows 11 laptop.

## Overview

This repository documents and scripts a practical local AI setup designed to run entirely on consumer hardware. No cloud APIs, no subscriptions - just your laptop doing useful AI work.

### Target Hardware
- Windows 11 laptop
- AMD Ryzen 7 4800H (8 cores / 16 threads)
- 32 GB RAM
- 6 GB VRAM (RX 5500M or similar)

### Core Stack
| Component | Tool | Purpose |
|-----------|------|---------|
| LLM Backend | **Ollama** | Single inference engine for all models |
| Coding Assistant | **VS Code + Continue** | AI-powered development environment |
| Chat Interface | **Jan** (or Open WebUI) | General-purpose conversation UI |
| Automation | **Python + Task Scheduler** | File management, backups, reports |

## Quick Start

### 1. Install Ollama
```powershell
# Download from https://ollama.com/download
# Or use winget:
winget install Ollama.Ollama
```

### 2. Pull Recommended Models
```powershell
ollama pull llama3.2              # General chat (3B)
ollama pull deepseek-coder-v2     # Coding (lite variant)
ollama pull nomic-embed-text      # Embeddings for RAG
```

### 3. Install Continue Extension
1. Open VS Code
2. Install "Continue" extension (continue.dev)
3. Point it to your local Ollama instance

### 4. Install Jan
```powershell
winget install Jan.Jan
# Or download from https://jan.ai
```

### 5. Install the CLI (optional)
```powershell
pip install -e .
vls --help
```

## Repository Structure

```
vansh-local-ai-stack/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── docs/
│   ├── architecture.md       # System design and data flow
│   ├── phases.md             # Implementation phases
│   ├── models.md             # Model selection guide
│   ├── automation.md         # Automation patterns
│   ├── rag.md                # RAG setup (future)
│   ├── agents.md             # Agent patterns (future)
│   ├── roadmap.md            # Long-term evolution
│   └── laptop-and-cloud.md   # Hybrid deployment notes
├── scripts/
│   ├── scan_drives.py        # Scan and catalog filesystem
│   ├── classify_files.py     # Intelligent file classification
│   ├── apply_moves.py        # Execute file reorganization
│   ├── disk_report.py        # Generate storage reports
│   ├── health_check.py       # System health monitoring
│   ├── generate_plan.py      # Move plan generation
│   └── examples/             # Helper scripts
├── config/
│   ├── .env.example          # Environment variables template
│   ├── scheduler-notes.md    # Windows Task Scheduler setup
│   └── n8n-setup-notes.md    # n8n automation guidance
└── .gitignore
```

## What You Can Do

### Coding
- Autocomplete, refactoring, and debugging in VS Code
- Multi-file context understanding
- Custom instructions for your codebase

### Automation
- Automatic file sorting by type/date/project
- Scheduled disk space reports
- Backup verification and health checks
- Move plan generation for batch file operations

### Knowledge Management (Phase 2+)
- RAG-powered document search
- Personal knowledge base queries
- Meeting notes and research organization

## Documentation

- [Architecture Overview](docs/architecture.md) - How components connect
- [Implementation Phases](docs/phases.md) - What to build when
- [Model Selection](docs/models.md) - Which models for which tasks
- [Automation Guide](docs/automation.md) - Script patterns and examples

## Why Local AI?

| Benefit | Description |
|---------|-------------|
| **Privacy** | Your code and documents never leave your machine |
| **Cost** | No API fees, no subscriptions |
| **Reliability** | Works offline, no rate limits |
| **Control** | Choose your models, customize behavior |

## Philosophy

This project prioritizes:
1. **Simplicity** - One inference backend (Ollama), not three
2. **Practicality** - Scripts you can run today, not aspirational architectures
3. **Growth** - Designed to expand into RAG, agents, and workflows later

## Contributing

This is a personal project but suggestions and improvements are welcome via issues and pull requests.

## License

MIT License - see [LICENSE](LICENSE)

---

**Status**: Documentation + starter scripts. Ready to run on a real Windows 11 laptop.
