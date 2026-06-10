# Setup Guide

> **New here?** Start with [GETTING_STARTED.md](GETTING_STARTED.md) for a non-technical walkthrough.

## Prerequisites

- Windows 10 or 11
- Python 3.10+ ([python.org](https://python.org))
- NVIDIA GPU with latest drivers (optional — falls back to CPU)

## One-Command Setup

```powershell
.\setup.ps1
```

This will:

1. Install Ollama (via winget) if not present
2. Pull required models:
   - `llama3.2` (3B) — general chat
   - `deepseek-coder-v2:lite` (2.5B) — code completion
   - `nomic-embed-text` (274M) — embeddings
3. Create Python virtual environment at `~/.local-ai-stack/venv`
4. Install Python dependencies
5. Copy `.env.example` → `.env`
6. Create data directories (logs, reports, catalogs, backups)
7. Set Ollama keep-alive=0 (zero idle resource usage)
8. Run `vls doctor` to verify everything is healthy
9. (Optional) Register scheduled tasks

The script is idempotent — safe to re-run anytime. Skipped steps are skipped.

## Manual Setup (if you prefer)

### 1. Install Ollama

```powershell
winget install Ollama.Ollama
```

### 2. Pull Models

```powershell
ollama pull llama3.2
ollama pull deepseek-coder-v2:lite
ollama pull nomic-embed-text
```

### 3. Install Python CLI

```powershell
python -m venv ~/.local-ai-stack/venv
~/.local-ai-stack/venv/Scripts/activate
pip install -e .
```

### 4. Configure

```powershell
copy config\.env.example .env
```

### 5. Verify

```powershell
vls doctor
```

## Scheduling Tasks (Optional)

Health check daily, disk report weekly, catalog backup monthly:

```powershell
.\setup.ps1  # re-run with admin privileges
```

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `vls` not found after setup | New PATH not loaded | Close and reopen PowerShell |
| Ollama not running | Service not started | Start "Ollama" from Start Menu |
| Setup hangs on model pull | Large download (~11 GB) | Wait — check task manager for network activity |
| GPU not detected | Unsupported GPU | Falls back to CPU automatically (slower but works) |
| `pip install` fails | Python version mismatch | Use Python 3.10–3.12 (3.14 may have issues) |
| Permission denied on Task Scheduler | Need admin rights | Re-run PowerShell as Administrator |
