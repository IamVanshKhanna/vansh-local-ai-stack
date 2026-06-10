# vansh-local-ai-stack

Lightweight local AI automation toolkit for Windows laptops. Ollama-backed Python CLI for file management, system monitoring, and scheduled automation — zero cloud, minimal idle resources.

## Target Hardware

- Windows 11
- NVIDIA GTX 1660 Ti (6 GB VRAM)
- 32 GB RAM
- AMD Ryzen 7 4800H (8C/16T)

## Quick Start

```powershell
.\setup.ps1
```

Runs everything: installs Ollama, pulls 3 models, creates venv, installs deps, copies config, schedules tasks.

## Commands

```
vls scan      — Scan filesystem and build a file catalog
vls classify  — Classify files by type/date/project
vls generate  — Generate move plans from classified files
vls apply     — Execute file reorganization (dry-run by default)
vls report    — Disk usage report
vls health    — Run specific health checks
vls doctor    — Full system health summary (run anytime)
```

## Resource Profile

| State | RAM | GPU | CPU |
|-------|-----|-----|-----|
| Idle | ~50 MB | 0% | 0% |
| Active (inference) | 2–6 GB | 2–6 GB VRAM | varies |
| Automation scripts | ~20 MB transient | 0% | brief |

Ollama runs as a Windows service with `OLLAMA_KEEP_ALIVE=0` — models unload when not in use.

## No Cloud. No API Keys. No Cost.

| Component | Cost |
|-----------|------|
| Ollama + Models | Free |
| Python scripts | Free |
| VS Code + Continue | Free |
| Task Scheduler | Built into Windows |
| **Total** | **$0/month** |
