# RAG (Retrieval Augmented Generation) Setup

This document outlines the approach for implementing local document search and retrieval.

## Overview

RAG enables LLMs to answer questions about your personal documents by:

1. **Indexing**: Convert documents to embeddings, store in vector DB
2. **Retrieval**: Find relevant documents for a query
3. **Generation**: LLM answers using retrieved context

```
Documents → Chunks → Embeddings → Vector DB
                                    │
Query → Embedding → Similarity Search → Retrieved Chunks
                                                    │
                                    Context + Query → LLM → Answer
```

---

## Components

### 1. Embedding Model: nomic-embed-text

**Why this model**:
- Small (274M params, <1GB VRAM)
- Fast inference
- Good quality for English text
- Available via Ollama

```bash
ollama pull nomic-embed-text
```

**Generate embeddings**:
```python
import requests

def get_embedding(text: str) -> list[float]:
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text
        }
    )
    return response.json()["embedding"]

# Usage
embedding = get_embedding("This is a sample document")
# Returns: 768-dimensional vector
```

---

### 2. Vector Database

**Options**:

| Database | Pros | Cons | Best For |
|----------|------|------|----------|
| ChromaDB | Python-native, simple setup | Less scalable | Quick start |
| Qdrant | Fast, filtering, persisted | Docker option | Production |
| FAISS | Very fast, simple | No metadata native | Script-based |

**Recommendation**: Start with ChromaDB for simplicity, migrate to Qdrant if needed.

#### ChromaDB Setup

```python
# Install
pip install chromadb

# Usage
import chromadb

client = chromadb.PersistentClient(path="~/.local-ai-stack/vector-db")
collection = client.create_collection("documents")

# Add documents
collection.add(
    documents=["Document 1 text", "Document 2 text"],
    metadatas=[{"source": "file1.pdf"}, {"source": "file2.pdf"}],
    ids=["doc1", "doc2"]
)

# Query
results = collection.query(
    query_texts=["search query"],
    n_results=5
)
```

#### Qdrant Setup (Docker)

```bash
# Run Qdrant locally
docker run -p 6333:6333 qdrant/qdrant
```

```python
from qdrant_client import QdrantClient

client = QdrantClient(":memory:")  # Or localhost:6333 for Docker

# Create collection
from qdrant_client.models import Distance, VectorParams

client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=768, distance=Distance.Cosine)
)
```

---

### 3. Document Processing Pipeline

#### Supported Formats

| Format | Library | Notes |
|--------|---------|-------|
| TXT | Built-in | Simple reading |
| MD | Built-in | Markdown parsing optional |
| PDF | PyPDF2, pdfplumber | Extract text |
| DOCX | python-docx | Extract paragraphs |
| HTML | BeautifulSoup | Strip tags |

```python
# Install
pip install pypdf2 python-docx beautifulsoup4

def read_document(path: str) -> str:
    ext = Path(path).suffix.lower()

    if ext == ".pdf":
        return read_pdf(path)
    elif ext == ".docx":
        return read_docx(path)
    elif ext in [".txt", ".md"]:
        return Path(path).read_text()
    else:
        raise ValueError(f"Unsupported format: {ext}")
```

#### Chunking Strategy

**Parameters**:
- **Chunk size**: 512-1024 tokens (for embedding model)
- **Overlap**: 50-100 tokens (preserve context across boundaries)
- **Method**: Fixed-size or semantic (paragraph-aware)

```python
def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks
```

**Better approach**: Use `langchain` for smarter chunking.

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)

chunks = splitter.split_text(document_text)
```

---

## Complete Pipeline

### Indexing Script

```python
import os
from pathlib import Path
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter

def index_documents(doc_dir: str, db_path: str):
    # Connect to vector DB
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection("documents")

    # Supported extensions
    extensions = {".txt", ".md", ".pdf", ".docx"}

    # Process each document
    for file_path in Path(doc_dir).rglob("*"):
        if file_path.suffix.lower() not in extensions:
            continue

        # Read and chunk
        text = read_document(str(file_path))
        chunks = chunk_text(text)

        # Generate embeddings and store
        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)

            collection.add(
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "source": str(file_path),
                    "chunk": i,
                }],
                ids=[f"{file_path.stem}_{i}"]
            )
```

### Query Script

```python
def query_rag(question: str, collection, n_results: int = 5) -> str:
    # Embed question
    question_embedding = get_embedding(question)

    # Search
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=n_results
    )

    # Build context
    context = "\n\n".join(results["documents"][0])

    # Generate answer
    prompt = f"""Answer the question based on the context below.

Context:
{context}

Question: {question}

Answer:"""

    return query_ollama(prompt, model="llama3.2")
```

---

## Directory Structure

```
~/.local-ai-stack/
├── vector-db/
│   └── chroma.sqlite3       # ChromaDB storage
├── documents/
│   ├── notes/              # Personal notes
│   ├── papers/             # Research papers
│   └── manuals/             # Technical docs
└── indexes/
    └── file_index.json     # Track indexed files
```

---

## Performance Optimization

### Batch Processing

When indexing many documents, batch embeddings:

```python
def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    # Ollama doesn't support batch embeddings directly
    # Use asyncio for parallel requests
    import asyncio
    import aiohttp

    async def embed_one(session, text):
        async with session.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text}
        ) as resp:
            return (await resp.json())["embedding"]

    async def batch_embed():
        async with aiohttp.ClientSession() as session:
            tasks = [embed_one(session, t) for t in texts]
            return await asyncio.gather(*tasks)

    return asyncio.run(batch_embed())
```

### Incremental Updates

Track indexed files to avoid reprocessing:

```python
import json
from hashlib import md5

def get_file_hash(path: str) -> str:
    return md5(Path(path).read_bytes()).hexdigest()

# Load index
index = json.loads(Path("file_index.json").read_text())

# Check if needs reindexing
current_hash = get_file_hash(doc_path)
if index.get(doc_path) != current_hash:
    reindex_document(doc_path)
    index[doc_path] = current_hash
```

---

## Integration with Chat UI

### Open WebUI

Open WebUI has built-in RAG support:
1. Settings → Documents
2. Enable document upload
3. Upload files or point to directory
4. Use `#` in chat to include documents

### Jan

Jan supports RAG via extensions or manual context injection.

### Custom Integration

Build a simple Flask/FastAPI wrapper:

```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/query")
async def query(question: str):
    answer = query_rag(question, collection)
    return {"answer": answer, "sources": sources}
```

---

## Use Cases

### Personal Knowledge Base

- Index: Notes, journal entries, bookmarks
- Query: "What did I write about project X?"
- Benefits: Find connections across years of writing

### Technical Documentation

- Index: API docs, manuals, code comments
- Query: "How do I configure the database connection?"
- Benefits: Query across multiple sources

### Research Papers

- Index: PDFs in a folder
- Query: "Papers discussing neural network optimization"
- Benefits: Semantic search beyond text matching

---

## Limitations

| Limitation | Mitigation |
|------------|------------|
| Context window | Use smaller chunks, filter results |
| Embedding quality | Fine-tune on domain (advanced) |
| No images | Use OCR for scanned docs (tesseract) |
| Query latency | Cache frequent queries |

---

## Future Enhancements

- **Hybrid search**: Combine vector + keyword (BM25)
- **Reranking**: Second model to rerank results
- **Multi-modal**: Include images with CLIP
- **Metadata filtering**: Filter by date, type, source

---

## Quick Start Checklist

- [ ] Install `chromadb` and `langchain`
- [ ] Pull `nomic-embed-text` model
- [ ] Create document directory
- [ ] Run indexing script
- [ ] Test query
- [ ] Integrate with chat UI (optional)

---

Next: [Agent Patterns](agents.md) for autonomous task execution.
