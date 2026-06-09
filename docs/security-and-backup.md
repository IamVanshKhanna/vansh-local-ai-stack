# Security and Backup Guide

This document covers security practices for a local-only AI stack, safe use of automation scripts, and backup recommendations.

---

## Local-Only Design

All AI inference runs on the user's laptop via Ollama. Tools — scripts, VS Code, Jan, n8n later — talk only to localhost unless you explicitly expose services. This gives you strong security by default:

| Property | Benefit |
|----------|---------|
| No outbound API calls | Code and documents never leave the machine |
| All services on localhost | No attack surface from the network |
| No user accounts in cloud | No credential theft vector |
| No telemetry by default | Ollama and Jan do not phone home |

### Service Binding

All services bind to `127.0.0.1` only:

```
Ollama       → 127.0.0.1:11434
Jan          → 127.0.0.1:3000 (if web mode)
Open WebUI   → 127.0.0.1:8080
n8n          → 127.0.0.1:5678
```

If you enable remote access (Tailscale, Cloudflare Tunnel), authentication becomes mandatory. See [laptop-and-cloud.md](laptop-and-cloud.md) for secure remote setup.

### Ollama API Security

Ollama has **no built-in authentication**. Anyone who can reach port 11434 can:
- Query any loaded model
- Pull or delete models
- Consume GPU resources

**Mitigations**:
- Never bind Ollama to `0.0.0.0`
- If using Tailscale, restrict access via ACLs
- If using Docker, keep Ollama on the host network
- Never expose Ollama directly to the public internet without a reverse proxy, auth, and TLS

---

## Main Risks

| Risk | Severity | Scenario |
|------|----------|----------|
| File automation errors | Medium | `classify_files.py` or `apply_moves.py` can move, rename, or delete files on the wrong paths if misconfigured |
| Misconfigured scheduling | Medium | Task Scheduler or n8n runs a script against the wrong directory, or runs it too frequently |
| Lost or stolen laptop | High | All data at rest is exposed; no cloud backup means total loss |
| Accidental port exposure | High | Binding Ollama or n8n to `0.0.0.0` lets anyone on the network use your models or workflows |

---

## Safe Use of Automation Scripts

### File Operation Safety

Scripts that modify the filesystem follow a **dry-run-first** policy:

1. `scan_drives.py` — Read-only, no safety concerns
2. `classify_files.py` — Read-only, no safety concerns
3. `apply_moves.py` — **Modifies files**, always defaults to dry-run
4. `disk_report.py` — Read-only, no safety concerns
5. `health_check.py` — Read-only, no safety concerns

### apply_moves.py Guardrails

This is the only script that moves files. It includes multiple safeguards:

| Guardrail | Behavior |
|-----------|----------|
| `--dry-run` default | Prints plan without executing |
| `--execute` required | Must be explicitly passed to make changes |
| Conflict detection | Skips if destination already exists |
| Validation pass | Checks source exists, parent dir exists |
| Operation log | Records every move for audit |

**Recommendation**: Always run `classify_files.py` and then `apply_moves.py` with `--dry-run` first. Review the output, then run with `--execute`.

### CSV Audit Logging

Always log moves to a CSV file for audit and recovery:

```bash
python scripts/apply_moves.py --plan moves.json --execute --output move_log.json
```

The `--output` flag writes a JSON log of every operation. For CSV logging, pipe the dry-run output:

```bash
python scripts/apply_moves.py --plan moves.json --dry-run \
    | python -c "import sys,json; [print(f'{m[\"source\"]},{m[\"destination\"]}') for m in json.load(sys.stdin).get('moves',[])]" \
    > move_audit_$(date +%Y%m%d).csv
```

Keep these logs indefinitely — they are your recovery record if files end up in the wrong place.

### Path Traversal Protection

Scripts validate paths before operating on them:

```python
# Scripts reject paths that escape allowed directories
SAFE_DIRS = [
    Path.home() / "Documents",
    Path.home() / "Downloads",
]

def safe_path(path: str) -> bool:
    resolved = Path(path).resolve()
    return any(resolved.is_relative_to(d) for d in SAFE_DIRS)
```

Never run scripts against system directories (`C:\Windows`, `/usr`, etc.).

### LLM Prompt Injection

When scripts send filenames or file contents to Ollama for classification, there is a theoretical risk of prompt injection via malicious filenames. Mitigations:

- Strip control characters from filenames before sending to LLM
- Limit LLM output to a fixed set of categories
- Never execute LLM output as code or shell commands
- Treat LLM classification as a suggestion, not authoritative

### Scheduled Task Safety

- Run scheduled tasks under your user account, not Administrator
- Set execution time limits (1 hour max) to prevent runaway scripts
- Use `--dry-run` for scheduled scans; only use `--execute` after manual review
- Log all scheduled task output for audit
- Double-check paths in scheduled tasks — a typo can target the wrong directory

---

## Backup Recommendations

### What to Back Up

| Priority | Data | Location | Method |
|----------|------|----------|--------|
| Critical | Repository (scripts, docs) | `vansh-local-ai-stack/` | Git + remote |
| Critical | Configuration | `.env`, Continue config | Git (sans secrets) |
| Important | Chat history | Jan data directory | File copy |
| Important | RAG index | `~/.local-ai-stack/vector-db/` | File copy |
| Replaceable | Models | `~/.ollama/models/` | Re-pull from Ollama |
| Replaceable | Catalogs | `~/.local-ai-stack/catalogs/` | Re-scan |

### Backup Strategy

#### 1. Git Repository (Recommended)

Push the repository to a private GitHub/GitLab remote:

```bash
git remote add origin https://github.com/youruser/vansh-local-ai-stack.git
git push -u origin main
```

**Exclude from Git**: `.env` files, database files, generated catalogs, logs.

#### 2. Configuration Backup

```powershell
# Export Continue configuration
copy "$HOME\.continue\config.json" "$HOME\.local-ai-stack\backups\continue-config.json"

# Export .env (ensure this backup is encrypted or stored securely)
copy "vansh-local-ai-stack\config\.env.example" "$HOME\.local-ai-stack\backups\"
```

#### 3. Full Stack Backup Script

```bash
# Run monthly
BACKUP_DIR="$HOME/.local-ai-stack/backups/$(date +%Y-%m)"

mkdir -p "$BACKUP_DIR"

# Chat history (Jan)
cp -r "$HOME/AppData/Local/Jan/data" "$BACKUP_DIR/jan-data/"

# RAG index (if exists)
cp -r "$HOME/.local-ai-stack/vector-db" "$BACKUP_DIR/vector-db/" 2>/dev/null

# Script logs
cp -r "$HOME/.local-ai-stack/logs" "$BACKUP_DIR/logs/" 2>/dev/null

echo "Backup saved to $BACKUP_DIR"
```

#### 4. Cloud Sync (Optional)

Use Syncthing or a cloud provider to sync backups off the laptop:

```
Laptop ~/.local-ai-stack/backups/
    │
    ▼ (Syncthing or rclone)
NAS / Cloud Storage
```

### Backup Cadence

| Frequency | What | How |
|-----------|------|-----|
| **Weekly** | Active work: this repo, config files, current chat history | `git push` + file copy to external SSD |
| **Monthly** | Archives: RAG indexes, old catalogs, full Jan data | File copy to external SSD or encrypted cloud drive |
| **On change** | `.env`, Continue config | Manual copy after edit |

Prioritise: (1) key docs and this repo, (2) config files (`.env`, Continue, Jan settings), (3) RAG indexes if/when they exist. Models are replaceable via `ollama pull` and should not be backed up.

### What NOT to Back Up

- **Ollama models** — Large (multiple GB), easily re-pulled via `ollama pull`
- **Python virtual environments** — Rebuilt with `pip install -r requirements.txt`
- **node_modules** — Rebuilt with `npm install`
- **Generated catalogs** — Recreated with `scan_drives.py`

### Restore Procedure

If the laptop is reset or the stack needs to be rebuilt:

1. Clone repository: `git clone <repo-url>`
2. Install Python deps: `pip install -r requirements.txt`
3. Copy `.env` from backup: `cp backup/.env config/.env`
4. Install Ollama: `winget install Ollama.Ollama`
5. Pull models: `ollama pull llama3.2 deepseek-coder-v2:lite nomic-embed-text`
6. Restore RAG index: `cp -r backup/vector-db ~/.local-ai-stack/`
7. Restore chat history: `cp -r backup/jan-data ~/AppData/Local/Jan/data/`
8. Run health check: `python scripts/health_check.py --check-all`

---

## Encryption

### Full-Disk Encryption

Enable BitLocker (Windows 11 Pro) or Device Encryption (Windows 11 Home):

```powershell
# Check BitLocker status
manage-bde -status C:
```

This protects all data at rest, including models, chat history, and RAG indexes.

### Sensitive Files

The `.env` file contains API keys and passwords. It is excluded from Git via `.gitignore`. Additional protection:

- Store `.env` in an encrypted volume (VeraCrypt) if using cloud sync
- Never commit `.env` to Git
- Use `config/.env.example` as the template, never the actual `.env`

---

## Security Checklist

- [ ] Ollama bound to localhost only (default)
- [ ] BitLocker / full-disk or folder encryption enabled
- [ ] `.env` excluded from Git
- [ ] `apply_moves.py` always reviewed via `--dry-run` before `--execute`
- [ ] Move operations logged to CSV/JSON and retained for audit
- [ ] Scheduled tasks run with time limits and correct paths
- [ ] No services exposed to internet without reverse proxy, auth, and TLS
- [ ] Regular backups of repo, config, and RAG indexes (external SSD or encrypted cloud)
- [ ] Backup tested (restore at least once)
- [ ] API keys rotated if ever accidentally committed

---

## Related

- [Architecture Overview](architecture.md) — System design
- [Laptop and Cloud](laptop-and-cloud.md) — Secure remote access
- [Automation Guide](automation.md) — Script patterns and safety
