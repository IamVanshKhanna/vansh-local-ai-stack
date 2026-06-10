"""Index documents for RAG — chunk text files, embed via Ollama, store in DB."""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from db.connection import get_connection, init_db
from db.rag_dal import upsert_document, set_document_status, insert_chunks


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

TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx",
    ".json", ".yaml", ".yml", ".csv", ".xml", ".html", ".css",
    ".cfg", ".ini", ".conf", ".toml", ".env", ".sql", ".sh", ".ps1",
    ".bat", ".rst", ".tex",
}

CHUNK_SIZE = 2048
CHUNK_OVERLAP = 256


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning("Could not read %s: %s", path, e)
        return ""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               chunk_overlap: int = CHUNK_OVERLAP) -> list[dict]:
    chunks = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        content = text[start:end]
        token_count = len(content.split())
        chunks.append({
            "index": index,
            "content": content,
            "token_count": token_count,
        })
        index += 1
        if end >= len(text):
            break
        start += chunk_size - chunk_overlap
        if start <= 0:
            break
    return chunks


def embed_text(text: str, model: str = "nomic-embed-text",
               host: str = "http://localhost:11434") -> list[float]:
    resp = requests.post(
        f"{host}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def index_paths(paths: list[str], recursive: bool = True,
                chunk_size: int = CHUNK_SIZE,
                chunk_overlap: int = CHUNK_OVERLAP,
                embed_model: str = "nomic-embed-text",
                ollama_host: str = "http://localhost:11434") -> dict:
    _init_rag_db()
    stats = {"total_files": 0, "indexed": 0, "skipped": 0, "failed": 0,
             "total_chunks": 0}

    file_paths: list[Path] = []
    for p in paths:
        path = Path(p).resolve()
        if not path.exists():
            logger.warning("Path does not exist: %s", path)
            stats["skipped"] += 1
            continue
        if path.is_file():
            file_paths.append(path)
        elif path.is_dir():
            pattern = "**/*" if recursive else "*"
            file_paths.extend(path.glob(pattern))

    seen = set()
    for fp in file_paths:
        if not fp.is_file():
            continue
        resolved = str(fp.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)

        if not is_text_file(fp):
            continue

        stats["total_files"] += 1
        doc_id = upsert_document(
            path=resolved,
            name=fp.name,
            extension=fp.suffix,
        )

        text = read_file(fp)
        if not text.strip():
            set_document_status(doc_id, "skipped", "Empty file")
            stats["skipped"] += 1
            continue

        chunks = chunk_text(text, chunk_size, chunk_overlap)
        if not chunks:
            set_document_status(doc_id, "skipped", "No chunks produced")
            stats["skipped"] += 1
            continue

        try:
            for chunk in chunks:
                chunk["embedding"] = embed_text(
                    chunk["content"], embed_model, ollama_host
                )
        except requests.RequestException as e:
            set_document_status(doc_id, "failed", str(e))
            stats["failed"] += 1
            continue

        insert_chunks(doc_id, chunks)
        set_document_status(doc_id, "completed", chunk_count=len(chunks))
        stats["indexed"] += 1
        stats["total_chunks"] += len(chunks)
        logger.info("Indexed %s (%s chunks)", fp.name, len(chunks))

    return stats
