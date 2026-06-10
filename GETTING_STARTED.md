# Getting Started with vansh-local-ai-stack

*For non-technical users — plain language, step by step.*

---

## What Is This?

This is a set of **smart helper tools** for your Windows laptop. It helps you:

- **Organize files** — scan folders and sort files by type
- **Monitor disk space** — check how much free space you have
- **Search your documents** — ask questions in plain English and get answers from your own notes, code, or research papers

Everything runs **100% on your laptop**. Nothing is uploaded to the cloud. No monthly fees. No API keys.

---

## Should I Use This?

| You want this if... | You DON'T want this if... |
|---|---|
| Your Downloads folder is a mess | You're happy with how your files are organized |
| You want to search your notes by asking questions | You use cloud tools like ChatGPT or Google |
| You're curious about running AI on your own computer | You don't have ~15 GB of free disk space |
| You use Windows 10 or 11 | You use macOS or Linux |

---

## Minimum Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| Operating System | Windows 10 | Windows 11 |
| Free Disk Space | 15 GB | 25 GB (if using document search) |
| RAM (Memory) | 8 GB | 16 GB |
| Processor | Any Intel or AMD | Any Intel or AMD |
| Graphics Card (GPU) | Not required (slower) | NVIDIA with 4+ GB VRAM (faster) |
| Internet (first time only) | Yes (to download AI models) | Broadband |
| Internet (daily use) | Not needed | Not needed |

---

## What Files Live Where?

```
vansh-local-ai-stack/         ← The main folder (you downloaded this)
│
├── setup.ps1                 ← Double-click this to install everything
├── GETTING_STARTED.md        ← This guide (you're reading it)
├── README.md                 ← Quick overview
├── SETUP.md                  ← Step-by-step setup details
├── CHANGELOG.md              ← Version history
│
├── vls.py                    ← The tool itself (don't edit)
│
├── scripts/                  ← Helper programs (don't edit)
│   ├── scan_drives.py        ← Scans your folders and lists files
│   ├── classify_files.py     ← Sorts files by type (documents, code, etc.)
│   ├── index_docs.py         ← Makes your documents searchable
│   ├── rag_query.py          ← Answers questions about your documents
│   ├── health_check.py       ← Checks if everything is working
│   └── apply_moves.py        ← Moves files into organized folders
│
├── config/
│   ├── .env.example          ← Settings (usually you don't need to change this)
│   └── tasks/                ← Scheduled task files
│
└── tests/                    ← Automated tests (don't touch)
```

---

## Step-by-Step Setup

### Step 1: Get the Project

Download or clone this repository from GitHub to your computer.

### Step 2: Run Setup

Right-click on `setup.ps1` and select **"Run with PowerShell"**.

> **What you'll see:** A black window will open. This is normal.
>
> **If Windows asks** "Do you want to allow this app to make changes?" — click **Yes**.
>
> **Wait 2-10 minutes.** You'll see green `[OK]` messages as each step completes.
>
> **What's happening:** The script is downloading three AI models (~11 GB total), creating a Python environment, and configuring everything.

### Step 3: Verify It Worked

Open a **new** PowerShell window and type:

```powershell
vls doctor
```

> **Expected output:** You should see all checks passing with `[PASS]` labels.
>
> **If you see** `"vls is not recognized"` — close PowerShell and open it again. Then try again.

---

## How to Use It — Simple Examples

| Command | What it does |
|---|---|
| `vls doctor` | Check if everything is working |
| `vls report` | See how much disk space is free |
| `vls scan -p "C:\Users\yourname\Documents" -o catalog.json` | List all files in your Documents folder |
| `vls index -p "C:\Users\yourname\Documents"` | Make your documents searchable |
| `vls query "what did I learn about Python?"` | Ask a question about your indexed documents |

---

## Troubleshooting

| Problem | What to do |
|---|---|
| `"vls is not recognized"` | Close PowerShell and open it again. Or type: `~\\.local-ai-stack\\venv\\Scripts\\vls` |
| `"Ollama is not running"` | Open Start Menu → search "Ollama" → click to start it. Then wait 10 seconds and try again. |
| Setup takes very long | The AI models are ~11 GB. Slow internet = longer wait. Let it finish. |
| `"CUDA error"` or GPU message | Your graphics card isn't supported. That's okay — it will use your CPU instead (slower but works). |
| `"Python not found"` | Download Python from https://python.org (version 3.10 or newer) and try again. |
| I see red error messages | Don't panic. Copy the error text and search it on Google, or report it on GitHub Issues. |

---

## What Next?

- **SETUP.md** — Technical details for advanced users
- **Scheduled tasks** — Set up automatic health checks and disk reports (see SETUP.md)
- **Index your projects** — Run `vls index -p "C:\Users\yourname\Projects"` to make your code searchable
- **Report issues** — Visit the GitHub repository and open an Issue

---

*Last updated: 2026-06-10*
