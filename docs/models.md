# Model Selection Guide

This document helps choose the right models for local inference given hardware constraints.

## Hardware Constraints

| Resource | Available | Impact |
|----------|-----------|--------|
| GPU VRAM | 6 GB | Limits model size for GPU inference |
| System RAM | 32 GB | Allows larger models on CPU (slower) |
| CPU Cores | 8 cores / 16 threads | Adequate for CPU inference |

### Model Sizing Math

Memory requirements for inference:

| Parameters | 4-bit Quant | 8-bit Quant | FP16 |
|------------|-------------|-------------|------|
| 3B | ~2 GB | ~4 GB | ~6 GB |
| 7B | ~4 GB | ~8 GB | ~14 GB |
| 13B | ~8 GB | ~16 GB | ~26 GB |
| 70B | ~40 GB | ~80 GB | ~140 GB |

**Rule**: Model size (GB) ≈ Parameters (B) × Size per B

**Our Constraints**:
- **GPU only**: ≤ 5B params (4-bit) for full context
- **Hybrid CPU-GPU**: Up to 7B with layer offloading
- **CPU only**: Up to 13B (slow, ~5 tokens/sec)

---

## Recommended Models

### 1. Llama 3.2 (3B) - General Purpose

**Best for**: Chat, general questions, light reasoning

**Pull**:
```bash
ollama pull llama3.2
```

**Characteristics**:
- 3B parameters
- ~2 GB VRAM (4-bit quantization)
- Fast inference (20-40 tokens/sec on GPU)
- Good general knowledge
- 128K context window

**When to use**:
- Casual conversation
- Quick questions
- Summarization
- Light coding help

---

### 2. DeepSeek Coder V2 (Lite) - Coding

**Best for**: Code completion, debugging, refactoring

**Pull**:
```bash
ollama pull deepseek-coder-v2:lite
```

**Characteristics**:
- ~2.5B parameters (lite variant)
- ~1.5 GB VRAM
- Excellent code understanding
- Multi-language support
- Good at explaining code

**When to use**:
- Autocomplete in VS Code
- Code generation
- Bug diagnosis
- Refactoring suggestions
- Code explanation

**Alternative**: `llama3.2` can also code effectively for simpler tasks.

---

### 3. Nomic Embed Text - Embeddings

**Best for**: RAG, semantic search, document indexing

**Pull**:
```bash
ollama pull nomic-embed-text
```

**Characteristics**:
- 274M parameters
- 768-dimensional embeddings
- Very fast
- Good for RAG pipelines

**When to use**:
- Document indexing for RAG
- Semantic similarity
- Clustering text
- Search applications

---

### 4. Phi-3 Mini (3.8B) - Reasoning

**Best for**: Math, logic, structured reasoning

**Pull**:
```bash
ollama pull phi3
```

**Characteristics**:
- 3.8B parameters
- ~2.5 GB VRAM (4-bit)
- Strong reasoning for size
- Good at math
- 128K context

**When to use**:
- Mathematical problems
- Logical deduction
- Step-by-step reasoning
- Technical explanations

---

### 5. Mistral 7B - Quality Alternative

**Best for**: Higher quality responses, complex tasks

**Pull**:
```bash
ollama pull mistral:7b
```

**Characteristics**:
- 7B parameters
- ~4 GB VRAM (4-bit)
- Higher quality than 3B models
- Slower but better
- May need CPU offloading

**When to use**:
- Complex reasoning
- Longer documents
- When quality > speed
- Creative writing

**Performance Note**: May run partially on CPU, achieving ~5-10 tokens/sec.

---

## Model Comparison Table

| Model | Params | VRAM | Speed | Quality | Use Case |
|-------|--------|------|-------|---------|----------|
| llama3.2 | 3B | 2 GB | Fast | Good | General |
| deepseek-coder-v2:lite | ~2.5B | 1.5 GB | Fast | Great for code | Coding |
| phi3 | 3.8B | 2.5 GB | Fast | Good reasoning | Math/Logic |
| mistral:7b | 7B | 4 GB | Medium | Very good | Quality |
| nomic-embed-text | 274M | <1 GB | Very fast | N/A | Embeddings |

---

## Model Management

### Listing Models

```bash
ollama list
```

### Model Details

```bash
ollama show llama3.2
```

### Updating Models

```bash
ollama pull llama3.2  # Updates to latest version
```

### Deleting Models

```bash
ollama rm old-model
```

### Custom Modelfile

Create a model variant with custom settings:

```dockerfile
# Modelfile
FROM llama3.2

# Set parameters
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 8192

# Set system prompt
SYSTEM You are a helpful coding assistant focused on Python development.

# Save as: ollama create my-coder -f Modelfile
```

Create custom model:
```bash
ollama create my-coder -f Modelfile
```

---

## Resource Monitoring

### Check GPU Usage

```powershell
# If using AMD
# AMD Software: Performance tab

# If using NVIDIA
nvidia-smi
```

### Check Ollama Logs

```powershell
# Windows - check log output in terminal where ollama serve runs
# Or check Event Viewer for Ollama service
```

### Monitor While Testing

```bash
# Run a query and watch memory usage
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Explain quantum computing in one paragraph"
}'
```

---

## Decision Flow

```
What do you need?
│
├── General chat/qa
│   └── Use: llama3.2
│
├── Coding help
│   ├── Autocomplete
│   │   └── Use: deepseek-coder-v2:lite
│   └── Complex code task
│       └── Use: llama3.2 or phi3
│
├── Math/Logic
│   └── Use: phi3
│
├── Higher quality needed
│   └── Use: mistral:7b (slower)
│
└── Document search (RAG)
    └── Use: nomic-embed-text + llama3.2
```

---

## Performance Expectations

| System | Model | Tokens/sec | Latency |
|-------|-------|------------|---------|
| GPU (6GB) | llama3.2 | 20-40 | <1s first token |
| GPU (6GB) | deepseek-coder-v2:lite | 25-50 | <1s |
| GPU (6GB) | phi3 | 15-30 | <1s |
| CPU | mistral:7b | 5-10 | 2-5s first token |
| CPU | llama3.2 | 10-20 | 1-2s |

**Note**: Actual performance varies based on context length, system load, and thermal throttling.

---

## Future Models to Watch

| Model | Expected Size | Notes |
|-------|---------------|-------|
| Llama 4 | Unknown | Next generation |
| DeepSeek V3 | Unknown | Better coding |
| Mistral NeMo | 12B | May be too large for GPU |

**Strategy**: Start with llama3.2 + phi3 + deepseek-coder. Add mistral:7b for quality tasks. Monitor new releases for quantized variants that fit in VRAM.

---

## Next Steps

- [Architecture Overview](architecture.md) - How these models fit into the system
- [Automation Guide](automation.md) - Using models in scripts
- [RAG Setup](rag.md) - Using nomic-embed-text for document search
