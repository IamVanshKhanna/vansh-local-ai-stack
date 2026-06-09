# Laptop and Cloud Integration

This document covers strategies for hybrid deployment, remote access, and cloud fallbacks.

---

## Philosophy

**Default**: Everything runs locally on the laptop.

**Optional**: Cloud integration for:
- Burst capacity (complex tasks)
- Remote access (from phone/other devices)
- Backup and sync (disaster recovery)
- Services not feasible locally

---

## Local-First Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    LAPTOP (Primary)                      │
│                                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │
│  │ Ollama  │  │  RAG    │  │ Scripts │  │  n8n    │   │
│  │         │  │ Vector  │  │ Python  │  │Workflows│   │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
            Optional Cloud Fallback
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    CLOUD (Fallback)                      │
│                                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                │
│  │ OpenAI  │  │Anthropic│  │  Sync   │                │
│  │   API   │  │   API   │  │ Service │                │
│  └─────────┘  └─────────┘  └─────────┘                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Cloud Fallback Strategy

### When to Use Cloud

| Scenario | Local | Cloud | Reason |
|----------|-------|-------|--------|
| Quick code help | Yes | No | Speed, privacy |
| Long document analysis | Try local | Fallback | Local may timeout |
| Complex reasoning | Try local | Fallback | Larger models available |
| Voice transcription | No | Maybe | Whisper API if local slow |
| Batch processing | Yes | No | Privacy, cost |
| Real-time collaboration | No | Yes | Sync required |

### Automatic Fallback

```python
def query_with_fallback(prompt: str, max_local_time: int = 30):
    """Try local first, fall back to cloud if needed."""

    # Try local Ollama
    try:
        with timeout(max_local_time):
            return query_ollama(prompt)
    except TimeoutError:
        logger.warning("Local inference timeout, using cloud fallback")
        return query_openai(prompt, model="gpt-4o-mini")
    except Exception as e:
        logger.error(f"Local inference failed: {e}")
        if local_unavailable():
            return query_openai(prompt)
        raise
```

### Cost Tracking

```python
# Track cloud API costs
CLOUD_COSTS = {
    "openai_gpt4_mini": 0.00015,  # per 1K tokens
    "anthropic_haiku": 0.00025,
}

def track_cost(provider: str, prompt_tokens: int, completion_tokens: int):
    cost = (
        prompt_tokens * CLOUD_COSTS[provider] +
        completion_tokens * CLOUD_COSTS[provider] * 2  # Completion costs more
    ) / 1000

    with open("cloud_costs.log", "a") as f:
        f.write(f"{datetime.now()},{provider},{cost}\n")
```

---

## Remote Access

### Option 1: Tailscale (Recommended)

**Setup**:
1. Install Tailscale on laptop
2. Install Tailscale on phone/other devices
3. Services accessible via Tailscale IP

**Benefits**:
- Free for personal use
- Encrypted mesh VPN
- No port forwarding
- Works behind NAT

**Access**:
```
# From phone, access laptop's Ollama
http://100.x.y.z:11434  # Tailscale IP

# Access Open WebUI
http://100.x.y.z:8080
```

### Option 2: Cloudflare Tunnel

**Setup**:
1. Install cloudflared
2. Create tunnel to localhost:11434
3. Access via cloudflare URL

**Benefits**:
- No VPN client needed
- Works from any browser
- Can add authentication

### Option 3: Local Network Only

If laptop and devices on same Wi-Fi:
```
# Find laptop IP
ipconfig  # Windows

# Access from phone
http://192.168.1.100:11434
```

**Security**: Only works at home, ensure firewall rules.

---

## Data Sync

### What to Sync

| Data | Sync Method | Frequency |
|------|-------------|-----------|
| Chat history | Syncthing or cloud | Real-time |
| RAG index | Manual or scheduled | Daily |
| Configuration | Git | On change |
| Documents | Syncthing | Real-time |
| Scripts | Git | On change |

### Syncthing Setup

**Both laptop and phone/other devices**:
1. Install Syncthing
2. Add folder: `~/.local-ai-stack`
3. Share between devices
4. Set to "receive only" on phone (optional)

**Synced contents**:
```
~/.local-ai-stack/
├── documents/      # Personal docs (if shared)
├── config/         # Chat UI configs
└── logs/          # Optional
```

**Not synced** (too large):
- `vector-db/` (rebuild on each device)
- `models/` (managed by Ollama)

---

## Phone Integration

### Scenario: AI from Phone

```
┌────────────┐          ┌─────────────┐
│   PHONE    │          │   LAPTOP    │
│           │          │             │
│  Chat App │◄────────►│  Ollama     │
│  (Open    │  Tailscale│  Open WebUI │
│   WebUI)   │          │             │
└────────────┘          └─────────────┘
```

**Setup**:
1. Run Open WebUI on laptop (Docker or native)
2. Install Tailscale on phone
3. Access Open WebUI via Tailscale IP
4. Chat history synced (if configured)

### Alternative: Self-Hosted Cloud

**If laptop isn't always on**:

```
┌────────────┐    ┌─────────────┐    ┌────────────┐
│   PHONE    │◄──►│ CLOUD VPS   │◄──►│   LAPTOP   │
│           │    │             │    │            │
│  Chat App │    │  Synced     │    │  Primary   │
│           │    │  Instance   │    │  Instance  │
└────────────┘    └─────────────┘    └────────────┘
```

**Cost**: ~$5/month for small VPS

---

## Cloud Services (Optional)

### Code Intelligence

If local models insufficient for complex code:

| Service | Use Case | Cost |
|---------|----------|------|
| GitHub Copilot | IDE autocomplete | $10/mo |
| Cursor | AI editor | $20/mo |
| Codeium | Free alternative | Free |

**Fallback strategy**: Use local for most tasks, cloud for complex refactoring.

### Voice Processing

| Service | Use Case | Cost |
|---------|----------|------|
| OpenAI Whisper API | Transcription (cloud) | $0.006/min |
| Local Whisper | Transcription (local) | Free |
| ElevenLabs | TTS | $5/mo |

**Recommendation**: Start with local Whisper, upgrade if quality insufficient.

### Reasoning Models

| Service | Use Case | Cost |
|---------|----------|------|
| OpenAI o1 | Complex reasoning | Higher |
| Claude 3.5 Sonnet | Analysis | Standard |
| Local mistral:7b | Basic reasoning | Free |

---

## Environment Configuration

### .env (Local Only)

```bash
# Local Ollama (primary)
OLLAMA_HOST=http://localhost:11434

# Cloud fallback (optional)
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# Sync service (optional)
SYNCTHING_API_KEY=xxx
```

### Conditional API Usage

```python
import os

USE_LOCAL = os.getenv("PREFER_LOCAL", "true").lower() == "true"
CLOUD_FALLBACK = bool(os.getenv("OPENAI_API_KEY"))

def smart_query(prompt: str):
    if USE_LOCAL:
        try:
            return query_ollama(prompt)
        except:
            if not CLOUD_FALLBACK:
                raise

    if CLOUD_FALLBACK:
        return query_openai(prompt)

    raise RuntimeError("No LLM backend available")
```

---

## Performance Comparison

| Task | Laptop (Local) | Cloud API |
|------|-----------------|-----------|
| Simple query | 2-5s | 1-3s + network |
| Code completion | Instant | 100-500ms |
| Long analysis | 30-60s | 5-15s |
| Batch processing | Hours (overnight) | Minutes + cost |

**Rule**: Local for frequent tasks, cloud for occasional complex tasks.

---

## Security Considerations

### Local Security

- All data stays on laptop
- No network exposure needed (except optional)
- Services run on localhost

### Cloud Security

- API keys in `.env`, never committed
- Minimal data sent (only prompts, not full context if avoidable)
- Audit cloud API logs

### Remote Access Security

- Tailscale provides encryption
- Don't expose services directly to internet
- Use strong device authentication

---

## Cost Comparison

### Full Local (Monthly)

| Item | Cost |
|------|------|
| Electricity | ~$5 (overnight inference) |
| Hardware | Already owned |
| **Total** | ~$5/month |

### Full Cloud (Monthly)

| Item | Cost |
|------|------|
| OpenAI API (heavy use) | ~$50-100 |
| Vector DB (cloud) | ~$25 |
| Sync service | ~$5 |
| **Total** | ~$80-130/month |

### Hybrid (Monthly)

| Item | Cost |
|------|------|
| Local inference | ~$5 |
| Cloud fallback (occasional) | ~$10 |
| **Total** | ~$15/month |

**Savings**: ~$100/month vs. full cloud

---

## Decision Matrix

```
Task requires:
├── Privacy? ───► Local
├── Speed? ───► Local (first token faster)
├── Complexity > local capability? ───► Cloud
├── Available offline? ───► Local only
└── Remote access needed? ───► Tailscale or Cloud UI
```

---

## Next Steps

1. Set up local stack first
2. Evaluate where local falls short
3. Add cloud fallback only if needed
4. Set up Tailscale if remote access needed
5. Add Syncthing for multi-device sync

See [Architecture](architecture.md) for local system design.
