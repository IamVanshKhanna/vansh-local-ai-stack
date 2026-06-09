# Windows Task Scheduler Setup

This guide explains how to wire Python scripts into Windows Task Scheduler for automated execution.

---

## Prerequisites

- Python installed and added to PATH
- Scripts cloned/downloaded to a known location
- Environment variables configured in `.env`

---

## Method 1: Task Scheduler GUI

### Open Task Scheduler

1. Press `Win + R`
2. Type `taskschd.msc`
3. Press Enter

### Create a Basic Task

1. Click "Create Basic Task" in the right panel
2. Name: "Local AI - Disk Report"
3. Description: "Weekly disk space report"
4. Click Next

### Set Trigger

1. Select "Weekly"
2. Choose day: Sunday
3. Choose time: 2:00 AM
4. Click Next

### Set Action

1. Select "Start a program"
2. Program/script: `C:\Python311\python.exe`
3. Add arguments:
   ```
   C:\path\to\vansh-local-ai-stack\scripts\disk_report.py --drives "C,D" --output C:\reports\disk_report.json
   ```
4. Start in: `C:\path\to\vansh-local-ai-stack\scripts`

### Finish

1. Check "Open the Properties dialog"
2. Click Finish

### Configure Properties

In the Properties dialog:

- **General tab**:
  - Select "Run whether user is logged on or not"
  - Check "Do not store password"
  - Select "Run with highest privileges"

- **Conditions tab**:
  - Uncheck "Start the task only if the computer is on AC power"
  - Or leave checked for laptop battery preservation

- **Settings tab**:
  - Check "Run task as soon as possible after a scheduled start is missed"
  - Set "Stop the task if it runs longer than": 1 hour

---

## Method 2: PowerShell

Create scheduled tasks via PowerShell for reproducibility.

### Disk Report Task (Weekly)

```powershell
# Create action
$action = New-ScheduledTaskAction `
    -Execute "C:\Python311\python.exe" `
    -Argument "C:\scripts\disk_report.py --drives C,D --output C:\reports\disk_report.json" `
    -WorkingDirectory "C:\scripts"

# Create trigger (weekly on Sunday at 2 AM)
$trigger = New-ScheduledTaskTrigger `
    -Weekly -WeeksInterval 1 -DaysOfWeek Sunday `
    -At 2am

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Register task
Register-ScheduledTask `
    -TaskName "LocalAI-DiskReport" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Weekly disk space report" `
    -RunLevel Highest
```

### Health Check Task (Daily)

```powershell
$action = New-ScheduledTaskAction `
    -Execute "C:\Python311\python.exe" `
    -Argument "C:\scripts\health_check.py --output C:\logs\health.json" `
    -WorkingDirectory "C:\scripts"

$trigger = New-ScheduledTaskTrigger `
    -Daily -At 6am

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask `
    -TaskName "LocalAI-HealthCheck" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Daily system health check"
```

### File Organization Task (Monthly)

```powershell
# Scan drives on 1st of each month
$action = New-ScheduledTaskAction `
    -Execute "C:\Python311\python.exe" `
    -Argument "C:\scripts\scan_drives.py --paths D:\,E:\ --output C:\catalogs\monthly_scan.json" `
    -WorkingDirectory "C:\scripts"

$trigger = New-ScheduledTaskTrigger `
    -Weekly -WeeksInterval 4 -DaysOfWeek Monday `
    -At 3am

Register-ScheduledTask `
    -TaskName "LocalAI-FileScan" `
    -Action $action `
    -Trigger $trigger `
    -Description "Monthly filesystem scan"
```

---

## Method 3: Batch File Wrapper

Use a batch file to set environment and handle logging.

### Create `run_disk_report.bat`

```batch
@echo off
REM Run disk report with logging

SET SCRIPT_DIR=C:\scripts\vansh-local-ai-stack\scripts
SET LOG_DIR=C:\logs
SET PYTHON=C:\Python311\python.exe

REM Create log directory if needed
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Run script with logging
"%PYTHON%" "%SCRIPT_DIR%\disk_report.py" ^
    --drives C,D ^
    --output "%LOG_DIR%\disk_report.json" ^
    >> "%LOG_DIR%\disk_report.log" 2>&1

echo Disk report completed at %date% %time% >> "%LOG_DIR%\disk_report.log"
```

### Schedule the Batch File

In Task Scheduler:
- Program/script: `C:\scripts\run_disk_report.bat`
- Start in: `C:\scripts`

---

## Logging

### Redirect Output

```powershell
# In Task Scheduler arguments, redirect output
python script.py >> C:\logs\script.log 2>&1
```

### Log Rotation

Use Python's `logging.handlers.RotatingFileHandler`:

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "script.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

---

## Troubleshooting

### Task Not Running

1. Check Task Scheduler History:
   - Task Scheduler > Click task > History tab

2. Check "Last Run Result":
   - 0x0 = Success
   - 0x1 = Incorrect function
   - 0x2 = File not found

3. Verify Python path:
   ```powershell
   where python
   ```

4. Test script manually:
   ```powershell
   python C:\scripts\health_check.py
   ```

### Permission Issues

- Ensure task runs as your user
- Check "Run with highest privileges"
- Verify script folder permissions

### Environment Variables

Environment variables are not inherited. Set in script or use `.env`:

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Recommended Schedule

| Task | Frequency | Time | Notes |
|------|-----------|------|-------|
| Health Check | Daily | 6:00 AM | Before work starts |
| Disk Report | Weekly | Sunday 2:00 AM | Low activity time |
| File Scan | Monthly | 1st Sunday 3:00 AM | Catalog updates |
| Backup Check | Weekly | Saturday 3:00 AM | Verify backups |

---

## Verifying Tasks

List all custom tasks:

```powershell
Get-ScheduledTask | Where-Object {$_.TaskPath -like "*LocalAI*"} | Format-Table TaskName, State, LastRunTime
```

Run task immediately for testing:

```powershell
Start-ScheduledTask -TaskName "LocalAI-HealthCheck"
```

---

## Removing Tasks

```powershell
Unregister-ScheduledTask -TaskName "LocalAI-HealthCheck" -Confirm:$false
```

---

## Export/Import Tasks

### Export

```powershell
Export-ScheduledTask -TaskName "LocalAI-HealthCheck" | Out-File "LocalAI-HealthCheck.xml"
```

### Import

```powershell
Register-ScheduledTask -Xml (Get-Content "LocalAI-HealthCheck.xml" | Out-String) -TaskName "LocalAI-HealthCheck"
```

---

Next: [n8n Setup Notes](n8n-setup-notes.md) for advanced workflows.
