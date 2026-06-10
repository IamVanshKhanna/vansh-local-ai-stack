"""Data access layer for the RAG pipeline (documents + chunks)."""

import json
import logging
import math
from typing import Optional

from .connection import get_connection

logger = logging.getLogger(__name__)


# ── Documents ────────────────────────────────────────────────────────

def upsert_document(path: str, name: str, extension: str = "",
                    file_type: str = "text",
                    file_id: Optional[int] = None) -> int:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM documents WHERE path = ?", (path,)
        ).fetchone()
        if existing:
            doc_id = existing["id"]
            conn.execute(
                """UPDATE documents SET status='pending', file_id=?, name=?,
                   extension=?, file_type=? WHERE id=?""",
                (file_id, name, extension, file_type, doc_id),
            )
        else:
            cursor = conn.execute(
                """INSERT INTO documents (path, name, extension, file_type, file_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (path, name, extension, file_type, file_id),
            )
            doc_id = cursor.lastrowid
        conn.commit()
    return doc_id


def set_document_status(doc_id: int, status: str, error: str = "",
                        chunk_count: int = 0) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE documents SET status=?, chunk_count=?, error=?
               WHERE id=?""",
            (status, chunk_count, error, doc_id),
        )
        conn.commit()


def get_document(doc_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return dict(row) if row else None


def list_documents(status: Optional[str] = None) -> list[dict]:
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM documents WHERE status = ? ORDER BY indexed_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY indexed_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def delete_document(doc_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()


# ── Chunks ───────────────────────────────────────────────────────────

def insert_chunks(document_id: int, chunks: list[dict]) -> None:
    if not chunks:
        return
    with get_connection() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO chunks
               (document_id, chunk_index, content, token_count, embedding)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (document_id, c["index"], c["content"],
                 c.get("token_count", 0),
                 json.dumps(c["embedding"]) if c.get("embedding") else None)
                for c in chunks
            ],
        )
        conn.commit()
    logger.info("Inserted %s chunks for document %s", len(chunks), document_id)


def get_chunks(document_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index",
            (document_id,),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d["embedding"]:
            d["embedding"] = json.loads(d["embedding"])
        result.append(d)
    return result


def get_all_chunks() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT c.*, d.path as doc_path, d.name as doc_name
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.embedding IS NOT NULL
            ORDER BY d.path, c.chunk_index
        """).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d["embedding"]:
            d["embedding"] = json.loads(d["embedding"])
        result.append(d)
    return result


def get_chunk_count() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
    return row[0] if row else 0


# ── Similarity search ────────────────────────────────────────────────

def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_similar(query_embedding: list[float], top_k: int = 5
                   ) -> list[dict]:
    all_chunks = get_all_chunks()
    scored = []
    for chunk in all_chunks:
        emb = chunk.get("embedding")
        if not emb or len(emb) == 0:
            continue
        score = cosine_similarity(query_embedding, emb)
        scored.append((score, chunk))
    scored.sort(key=lambda x: -x[0])
    return [{"score": s, **c} for s, c in scored[:top_k]]
