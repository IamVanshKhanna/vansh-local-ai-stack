# n8n Setup Notes

This guide explains how to set up n8n for complex automation workflows in the local AI stack.

---

## What is n8n?

n8n is a workflow automation tool (like Zapier or Make) that you can run locally. It allows creating multi-step workflows with triggers, conditions, and integrations.

**Use Cases**:
- Email to task conversion
- File processing pipelines
- Webhook-triggered automations
- Scheduled multi-step tasks
- Integration between local scripts and external services

---

## Installation

### Option 1: npm (Recommended for Local)

```bash
# Install n8n globally
npm install -g n8n

# Run n8n
n8n start
```

n8n will be available at http://localhost:5678

### Option 2: Docker

```powershell
# Pull and run n8n container
docker run -it --rm `
    --name n8n `
    -p 5678:5678 `
    -v ~/.n8n:/home/node/.n8n `
    n8nio/n8n
```

### Option 3: Desktop App

Download from: https://n8n.io/download/

---

## Configuration

### Environment Variables

Create `.env` in the n8n directory:

```bash
# n8n config
N8N_HOST=localhost
N8N_PORT=5678
N8N_PROTOCOL=http

# Security (set a strong password!)
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your-secure-password

# Database (SQLite by default, can use PostgreSQL)
DB_TYPE=sqlite

# Timezone
GENERIC_TIMEZONE=America/New_York
```

### Running with Environment File

```bash
n8n start --config=~/.n8n/.env
```

---

## Initial Setup

### 1. Create Admin Account

1. Open http://localhost:5678
2. Create owner account
3. Set strong password

### 2. Configure Credentials

Add credentials for services you'll use:

- Local scripts (HTTP Request to localhost)
- Email (SMTP)
- Webhooks (for triggers)

### 3. Create First Workflow

Click "Add Workflow" to create a new automation.

---

## Example Workflows

### Workflow 1: Health Check Alert

**Trigger**: Daily at 7:00 AM
**Steps**:
1. **Schedule Trigger**: Daily 7:00 AM
2. **Execute Command**: Run `health_check.py`
3. **If**: Status != "healthy"
4. **Email**: Send alert notification

**JSON Template**:
```json
{
  "name": "Health Check Alert",
  "nodes": [
    {
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": {"interval": [{"field": "hours", "hoursInterval": 24}]}
      }
    },
    {
      "type": "n8n-nodes-base.executeCommand",
      "parameters": {
        "command": "python C:\\scripts\\health_check.py --output result.json"
      }
    },
    {
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {
          "string": [{"value1": "={{$json.status}}", "value2": "healthy"}]
        }
      }
    },
    {
      "type": "n8n-nodes-base.emailSend",
      "parameters": {
        "subject": "Health Check Alert",
        "text": "Health check failed: {{JSON.stringify($json)}}"
      }
    }
  ]
}
```

### Workflow 2: File Organization Pipeline

**Trigger**: Manual or Webhook
**Steps**:
1. **Webhook**: Receive scan request
2. **Execute Command**: Run `scan_drives.py`
3. **Execute Command**: Run `classify_files.py`
4. **Email**: Send classification report

### Workflow 3: RAG Index Update

**Trigger**: Webhook from document upload
**Steps**:
1. **Webhook**: Receive document path
2. **HTTP Request**: Call indexing API
3. **Database**: Update index status in SQLite
4. **Slack/Email**: Notify completion

---

## Integration with Python Scripts

### Method 1: Execute Command Node

Run Python scripts directly:

```javascript
// Command
python C:\scripts\scan_drives.py --paths "{{$json.paths}}" --output scan.json
```

**Pros**: Simple, direct execution
**Cons**: Limited output parsing

### Method 2: HTTP Request Node

Create a simple Flask/FastAPI server:

```python
# server.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ScanRequest(BaseModel):
    paths: str

@app.post("/scan")
def scan(req: ScanRequest):
    # Run scan
    result = run_scan(req.paths)
    return {"status": "success", "catalog": result}
```

Run the server:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

In n8n, use HTTP Request node to call:
```
POST http://localhost:8000/scan
Body: {"paths": "D:\\,E:\\"}
```

### Method 3: Trigger via Webhook

Have Python scripts call n8n webhooks:

```python
import requests

def notify_n8n(event: str, data: dict):
    webhook_url = "http://localhost:5678/webhook/scan-complete"
    requests.post(webhook_url, json={"event": event, **data})
```

---

## Connecting to Ollama

n8n can call Ollama for LLM-powered decisions:

```javascript
// HTTP Request node to Ollama
{
  "method": "POST",
  "url": "http://localhost:11434/api/generate",
  "headers": {"Content-Type": "application/json"},
  "body": {
    "model": "llama3.2",
    "prompt": "Classify this file: {{$json.filename}}",
    "stream": false
  }
}
```

---

## Persisting Workflows

Workflows are saved in:
- `~/.n8n/database.sqlite` (SQLite mode)
- Or environment-configured database

### Backup Workflows

```bash
# Export specific workflow
n8n export:workflow --id=123 --output=workflow.json

# Or use n8n UI: Settings > Export
```

### Import Workflows

```bash
n8n import:workflow --input=workflow.json
```

---

## Security Considerations

### Local Network Only

By default, n8n binds to localhost. To allow LAN access:

```bash
N8N_HOST=0.0.0.0 n8n start
```

**Warning**: Set up authentication if exposed to network.

### HTTPS

For secure access, use reverse proxy (nginx, Caddy):

```nginx
# nginx config
server {
    listen 443 ssl;
    server_name n8n.local;

    location / {
        proxy_pass http://localhost:5678;
        proxy_set_header Host $host;
    }
}
```

---

## Performance Tuning

### Execution Timeout

Default timeout is 5 minutes. Adjust for long-running scripts:

```bash
EXECUTIONS_TIMEOUT=3600000  # 1 hour in ms
```

### Concurrency

Limit concurrent executions:

```bash
EXECUTIONS_DATA_SAVE_ON_ERROR=all
EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
```

---

## Workflow Templates

Save workflow templates in `config/n8n-workflows/`:

```
config/
└── n8n-workflows/
    ├── health-check-alert.json
    ├── file-organization.json
    └── rag-index-update.json
```

---

## Troubleshooting

### n8n Won't Start

1. Check port 5678 is not in use:
   ```powershell
   netstat -ano | findstr :5678
   ```

2. Check npm/node versions:
   ```bash
   npm install -g npm@latest
   ```

### Workflow Execution Errors

1. Check execution logs in n8n UI
2. Enable verbose logging:
   ```bash
   N8N_LOG_LEVEL=debug n8n start
   ```

### Scripts Not Running

1. Verify Python path in workflow
2. Test command manually
3. Check script permissions

---

## Recommended Workflow Schedule

| Workflow | Trigger | Frequency | Notes |
|----------|---------|-----------|-------|
| Health Check Alert | Schedule | Daily 7 AM | Alert on failures |
| Disk Report | Schedule | Weekly | Sunday 2 AM |
| File Organization | Manual | On demand | Review before execute |
| RAG Index Update | Webhook | On document add | Batch uploads |

---

## Resources

- [n8n Documentation](https://docs.n8n.io)
- [n8n Community](https://community.n8n.io)
- [n8n Workflow Templates](https://n8n.io/workflows)

---

Next: [Architecture](../docs/architecture.md) to understand system design.
