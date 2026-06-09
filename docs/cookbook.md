# Cookbook — Example Scenarios

Step-by-step recipes for common tasks using the local AI stack. Each recipe lists which scripts or tools you need, the exact commands to run, and what to expect.

---

## Recipe 1: Weekly Drive Clean-Up

**Goal**: Tidy your drives every Sunday — scan, classify, review, move, then report.

**Tools**: `scan_drives.py`, `classify_files.py`, `apply_moves.py`, `disk_report.py`

### Step 1 — Scan

```bash
python scripts/scan_drives.py --paths "D:\,E:\" --output D:\catalogs\weekly_scan.json --verbose
```

Expected output:
```
2024-01-14 02:00:05 - INFO - Scanning: D:\
2024-01-14 02:03:42 - INFO - Scanning: E:\
2024-01-14 02:06:11 - INFO - Scan complete: 14832 files, 187.3 GB
2024-01-14 02:06:11 - INFO - Saved 14832 files to D:\catalogs\weekly_scan.json

Scan Summary:
  Files scanned: 14832
  Total size: 187.3 GB

Top 10 extensions:
  .pdf: 2104 files
  .jpg: 1893 files
  .docx: 1022 files
  ...
```

### Step 2 — Classify

```bash
python scripts/classify_files.py \
    --input D:\catalogs\weekly_scan.json \
    --output D:\catalogs\weekly_classified.json \
    --use-llm \
    --model llama3.2
```

Expected output:
```
Classification Summary:
  Total files: 14832

Categories:
  documents: 3126 (21.1%)
  media: 2890 (19.5%)
  code: 1844 (12.4%)
  archives: 1202 (8.1%)
  downloads: 987 (6.7%)
  ...
```

### Step 3 — Manual Review

Open `weekly_classified.json` and review the `category` field for files you care about. Fix any mis-classifications by editing the JSON directly, or adjust the rules in the script.

### Step 4 — Apply Moves (Dry-Run First)

Create a move plan that maps categories to target folders. Save as `moves.json`:

```json
{
  "moves": [
    {"source": "D:\\Downloads\\report.pdf", "destination": "D:\\Organized\\Documents\\report.pdf", "size": 1024000, "category": "documents"},
    {"source": "D:\\Downloads\\photo.jpg", "destination": "D:\\Organized\\Media\\photo.jpg", "size": 2048000, "category": "media"}
  ]
}
```

Dry-run:

```bash
python scripts/apply_moves.py --plan moves.json --dry-run --verbose
```

Expected output:
```
DRY RUN: Would process 2 moves
  D:\Downloads\report.pdf -> D:\Organized\Documents\report.pdf
  D:\Downloads\photo.jpg -> D:\Organized\Media\photo.jpg

Move Results:
  Total operations: 2
  Successful: 0
  Failed: 0
  Skipped: 0

  This was a DRY RUN. No files were moved.
  Use --execute to apply changes.
```

### Step 5 — Execute

```bash
python scripts/apply_moves.py --plan moves.json --execute --output D:\logs\move_log_20240114.json
```

### Step 6 — Report

```bash
python scripts/disk_report.py --drives "D,E" --format markdown --output D:\reports\weekly_report_20240114.md
```

---

## Recipe 2: Daily Downloads / Desktop Tidy

**Goal**: Automatically sort new files in Downloads and Desktop into category folders every day.

**Tools**: `scan_drives.py`, `classify_files.py`, `apply_moves.py`, Windows Task Scheduler

### Configure Classification

`classify_files.py` already handles Downloads/Desktop paths via its path-based rules (the `downloads` category). For Desktop, add a custom rule in the script or rely on the extension-based rules.

### Scan and Classify (One-Liner)

```bash
python scripts/scan_drives.py --paths "C:\Users\You\Downloads,C:\Users\You\Desktop" --output C:\catalogs\daily_scan.json && python scripts/classify_files.py --input C:\catalogs\daily_scan.json --output C:\catalogs\daily_classified.json
```

### Apply Moves (Review Then Execute)

```bash
# Dry-run
python scripts/apply_moves.py --plan daily_moves.json --dry-run

# After review
python scripts/apply_moves.py --plan daily_moves.json --execute --output C:\logs\daily_move_log.json
```

### Wire into Task Scheduler

Reference: [scheduler-notes.md](../config/scheduler-notes.md)

```powershell
$action = New-ScheduledTaskAction `
    -Execute "C:\Python311\python.exe" `
    -Argument "C:\scripts\vansh-local-ai-stack\scripts\scan_drives.py --paths 'C:\Users\You\Downloads,C:\Users\You\Desktop' --output C:\catalogs\daily_scan.json" `
    -WorkingDirectory "C:\scripts\vansh-local-ai-stack\scripts"

$trigger = New-ScheduledTaskTrigger -Daily -At 7am

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask `
    -TaskName "LocalAI-DailyTidy" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Daily Downloads/Desktop scan"
```

**Important**: Schedule the *scan and classify* step only. Review the classification manually before running `apply_moves.py --execute`. Do not auto-execute moves without review.

---

## Recipe 3: Gmail Triage (with Optional n8n)

**Goal**: Summarise and categorise unread emails daily using a local LLM.

**Tools**: n8n (optional), Ollama, `health_check.py`

### High-Level Flow

```
Unread emails → Pull via n8n (or manual export) → Summarise/categorise via Ollama → Daily summary file
```

### Manual Approach (No n8n)

1. Export unread emails from Gmail as a text file (or copy-paste subjects/bodies).
2. Save to `~/mail/inbox_today.txt`.
3. Run a one-shot LLM classification:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Categorise each email below into one of: urgent, reply-today, low-priority, newsletter. Output a table with columns: Subject, Category, One-line summary.\n\nEmails:\n'"$(cat ~/mail/inbox_today.txt)"'",
  "stream": false
}' > ~/mail/triage_$(date +%Y%m%d).json
```

### n8n Approach

Use the example workflow: [gmail_triage_example.json](../config/n8n/gmail_triage_example.json)

The workflow:
1. **Gmail Trigger** — Polls for unread emails every 30 minutes
2. **Function Node** — Extracts subject, sender, body
3. **HTTP Request → Ollama** — Sends a classification prompt:
   ```
   "Categorise this email into: urgent / reply-today / low-priority / newsletter.
   Subject: {subject}
   From: {sender}
   Body: {body}
   Category:"
   ```
4. **If Node** — Routes urgent items to a Todoist task, newsletters to archive
5. **Write File Node** — Appends daily summary to `~/mail/daily_summary.md`

Reference: [n8n Setup Notes](../config/n8n-setup-notes.md), [Automation Guide](automation.md)

### Pre-Flight Check

Before running either approach, verify Ollama is up:

```bash
python scripts/health_check.py --only ollama
```

Expected output:
```json
{
  "status": "healthy",
  "checks": {
    "ollama": {"status": "pass", "host": "http://localhost:11434", "latency_ms": 12}
  }
}
```

---

## Recipe 4: Job Application / Outreach Helper

**Goal**: Use Jan (or Open WebUI) with a local model to draft tailored cover emails and LinkedIn notes.

**Tools**: Jan or Open WebUI, Ollama (`llama3.2` or `mistral:7b`)

### Draft a Cover Email

Open Jan, select **llama3.2** (or **mistral:7b** for higher quality), and paste this prompt:

```
You are a professional email writer. Draft a short cover email (under 150 words) for a job application.

Job posting:
---
{paste the job ad here}
---

My background:
---
{paste your 3-4 line personal profile: role, years of experience, key skills}
---

The email should:
- Reference a specific detail from the job posting
- Highlight one relevant achievement
- Be warm but professional, not generic
- End with a clear call to action
```

### Draft a LinkedIn Connection Note

Same chat, new prompt:

```
Draft a LinkedIn connection request note (under 300 characters) for a hiring manager at {company name}.

Context: I saw their post about {topic} and I'm interested in the {role} position.

Tone: Professional, brief, specific to their content.
```

### Reusable Prompt Snippets

Save these as system prompts or quick-access notes in Jan:

**Cover email template**:
```
Draft a cover email for: {{job_ad}}
My profile: {{profile}}
Constraints: under 150 words, reference one detail from the ad, one achievement, warm-professional tone.
```

**LinkedIn note template**:
```
Draft a LinkedIn connection note for: {{contact_role}} at {{company}}
Reason: {{reason}}
Constraints: under 300 characters, reference their content, professional tone.
```

**Follow-up email template**:
```
Draft a polite follow-up email sent 5 days after applying to: {{company}} for {{role}}.
Keep it under 80 words. Do not sound desperate.
```

### Tips

- Use **mistral:7b** for longer or more nuanced drafts (slower but higher quality)
- Use **llama3.2** for quick iterations and short notes
- Keep your personal profile as a note in Jan so you can paste it into prompts easily
- Never paste sensitive personal details (SSN, address) into prompts — use placeholders
