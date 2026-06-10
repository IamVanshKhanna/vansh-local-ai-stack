"""RAG query engine — embed a question, find relevant chunks, answer via LLM."""

from __future__ import annotations

import logging

import requests

from db.connection import get_connection, init_db
from db.rag_dal import search_similar, get_chunk_count


def _init_rag_db():
    """Initialize both base schema and RAG schema."""
    init_db()
    from pathlib import Path as _P
    schema = _P(__file__).parent / "db" / "schema_rag.sql"
    if schema.exists():
        with get_connection() as conn:
            conn.executescript(schema.read_text())
            conn.commit()

logger = logging.getLogger(__name__)


def embed_text(text: str, model: str = "nomic-embed-text",
               host: str = "http://localhost:11434") -> list[float]:
    resp = requests.post(
        f"{host}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def build_prompt(query: str, context_chunks: list[dict]) -> str:
    context_parts = []
    for i, c in enumerate(context_chunks, 1):
        source = c.get("doc_name", c.get("doc_path", "unknown"))
        context_parts.append(
            f"[{i}] (from {source})\n{c['content']}"
        )
    context = "\n\n".join(context_parts)

    prompt = f"""You are a helpful assistant answering questions based on the provided context.

Context:
{context}

Question: {query}

Answer the question based only on the provided context. If the context does not contain enough information, say so clearly. Be concise and specific."""
    return prompt


def query(query: str, top_k: int = 5,
          embed_model: str = "nomic-embed-text",
          llm_model: str = "llama3.2",
          ollama_host: str = "http://localhost:11434") -> dict:
    _init_rag_db()

    chunk_count = get_chunk_count()
    if chunk_count == 0:
        return {
            "query": query,
            "answer": "No documents have been indexed yet. Run 'vls index' first.",
            "sources": [],
            "chunks_used": 0,
        }

    query_embedding = embed_text(query, embed_model, ollama_host)
    results = search_similar(query_embedding, top_k)

    if not results:
        return {
            "query": query,
            "answer": "No relevant content found in indexed documents.",
            "sources": [],
            "chunks_used": 0,
        }

    prompt = build_prompt(query, results)
    resp = requests.post(
        f"{ollama_host}/api/generate",
        json={"model": llm_model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    answer = resp.json()["response"]

    sources = []
    seen_docs = set()
    for r in results:
        doc_id = r.get("document_id")
        if doc_id and doc_id not in seen_docs:
            seen_docs.add(doc_id)
            sources.append({
                "document_id": doc_id,
                "name": r.get("doc_name", ""),
                "path": r.get("doc_path", ""),
                "score": round(r["score"], 4),
            })

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": len(results),
    }
