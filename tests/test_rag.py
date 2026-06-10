"""Tests for the RAG pipeline (indexing, embeddings, querying)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from db.connection import get_connection, init_db, set_db_path
from db.rag_dal import (
    upsert_document, set_document_status, get_document, list_documents,
    delete_document, insert_chunks, get_chunks, get_all_chunks,
    cosine_similarity, search_similar, get_chunk_count,
)
from index_docs import is_text_file, chunk_text, embed_text, read_file


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    db_path = tmp_path / "test.db"
    set_db_path(db_path)
    init_db()
    # Also init RAG schema
    rag_schema = Path(__file__).parent.parent / "scripts" / "db" / "schema_rag.sql"
    with get_connection() as conn:
        conn.executescript(rag_schema.read_text())
        conn.commit()


# ── Document DAL ─────────────────────────────────────────────────────

class TestDocuments:
    def test_upsert_new(self):
        doc_id = upsert_document("/path/to/doc.md", "doc.md", ".md")
        assert doc_id > 0
        doc = get_document(doc_id)
        assert doc["path"] == "/path/to/doc.md"
        assert doc["status"] == "pending"

    def test_upsert_update(self):
        doc_id = upsert_document("/path/to/doc.md", "doc.md", ".md")
        upsert_document("/path/to/doc.md", "doc.md", ".md", file_id=None)
        doc = get_document(doc_id)
        assert doc["file_id"] is None

    def test_set_status(self):
        doc_id = upsert_document("/path/to/doc.md", "doc.md", ".md")
        set_document_status(doc_id, "completed", chunk_count=5)
        doc = get_document(doc_id)
        assert doc["status"] == "completed"
        assert doc["chunk_count"] == 5

    def test_list_documents(self):
        upsert_document("/a.md", "a.md")
        upsert_document("/b.md", "b.md")
        docs = list_documents()
        assert len(docs) == 2

    def test_list_filtered(self):
        d1 = upsert_document("/a.md", "a.md")
        d2 = upsert_document("/b.md", "b.md")
        set_document_status(d1, "completed")
        set_document_status(d2, "failed")
        completed = list_documents("completed")
        assert len(completed) == 1
        assert completed[0]["id"] == d1

    def test_delete(self):
        doc_id = upsert_document("/a.md", "a.md")
        delete_document(doc_id)
        assert get_document(doc_id) is None


# ── Chunk DAL ────────────────────────────────────────────────────────

class TestChunks:
    def test_insert_and_get(self):
        doc_id = upsert_document("/doc.md", "doc.md")
        chunks = [
            {"index": 0, "content": "Hello world", "token_count": 2,
             "embedding": [0.1, 0.2, 0.3]},
            {"index": 1, "content": "Foo bar baz", "token_count": 3,
             "embedding": [0.4, 0.5, 0.6]},
        ]
        insert_chunks(doc_id, chunks)
        stored = get_chunks(doc_id)
        assert len(stored) == 2
        assert stored[0]["content"] == "Hello world"
        assert stored[0]["embedding"] == [0.1, 0.2, 0.3]

    def test_insert_without_embedding(self):
        doc_id = upsert_document("/doc.md", "doc.md")
        chunks = [{"index": 0, "content": "No embedding", "token_count": 2}]
        insert_chunks(doc_id, chunks)
        stored = get_chunks(doc_id)
        assert stored[0]["embedding"] is None

    def test_get_all_chunks(self):
        d1 = upsert_document("/a.md", "a.md")
        d2 = upsert_document("/b.md", "b.md")
        insert_chunks(d1, [{"index": 0, "content": "A content",
                            "token_count": 2, "embedding": [0.1]}])
        insert_chunks(d2, [{"index": 0, "content": "B content",
                            "token_count": 2, "embedding": [0.2]}])
        all_c = get_all_chunks()
        assert len(all_c) == 2

    def test_get_chunk_count(self):
        d1 = upsert_document("/a.md", "a.md")
        insert_chunks(d1, [
            {"index": 0, "content": "C1", "token_count": 1},
            {"index": 1, "content": "C2", "token_count": 1},
        ])
        assert get_chunk_count() == 2


# ── Similarity Search ────────────────────────────────────────────────

class TestSimilarity:
    def test_cosine_similarity_identical(self):
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_cosine_similarity_partial(self):
        sim = cosine_similarity([1, 0, 0], [1, 1, 0])
        assert 0.5 < sim < 1.0

    def test_cosine_similarity_zero_vector(self):
        assert cosine_similarity([0, 0], [1, 0]) == pytest.approx(0.0)

    def test_search_similar(self):
        d1 = upsert_document("/python.md", "python.md")
        insert_chunks(d1, [
            {"index": 0, "content": "Python is a programming language",
             "token_count": 5, "embedding": [1.0, 0.0]},
            {"index": 1, "content": "Cats are furry animals",
             "token_count": 4, "embedding": [0.0, 1.0]},
        ])
        query_emb = [0.9, 0.1]
        results = search_similar(query_emb, top_k=2)
        assert len(results) >= 1
        assert "python" in results[0]["content"].lower()
        assert results[0]["score"] > 0.5

    def test_search_similar_empty_corpus(self):
        results = search_similar([1.0, 0.0], top_k=5)
        assert results == []


# ── Chunking ─────────────────────────────────────────────────────────

class TestChunking:
    def test_chunk_short_text(self):
        text = "Hello world"
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
        assert len(chunks) == 1
        assert chunks[0]["content"] == text

    def test_chunk_long_text(self):
        text = "A" * 5000
        chunks = chunk_text(text, chunk_size=2048, chunk_overlap=256)
        assert len(chunks) > 1
        assert chunks[0]["index"] == 0
        assert chunks[-1]["index"] == len(chunks) - 1

    def test_chunk_overlap(self):
        text = "X" * 1000
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
        for c in chunks:
            assert c["token_count"] > 0

    def test_chunk_empty_text(self):
        assert chunk_text("", chunk_size=100, chunk_overlap=10) == []

    def test_chunk_token_count(self):
        text = "one two three four five"
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
        assert chunks[0]["token_count"] == 5


# ── File helpers ─────────────────────────────────────────────────────

class TestFileHelpers:
    def test_is_text_file(self):
        assert is_text_file(Path("file.py"))
        assert is_text_file(Path("notes.md"))
        assert is_text_file(Path("config.json"))
        assert not is_text_file(Path("image.jpg"))
        assert not is_text_file(Path("doc.pdf"))
        assert not is_text_file(Path("archive.zip"))

    def test_read_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        assert read_file(f) == "hello"

    def test_read_nonexistent(self, tmp_path):
        assert read_file(tmp_path / "nope.txt") == ""


# ── Embedding API (mocked) ───────────────────────────────────────────

class TestEmbedding:
    def test_embed_text(self):
        mock_resp = {"embedding": [0.1, 0.2, 0.3]}
        with patch("index_docs.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_resp
            result = embed_text("hello")
            assert result == [0.1, 0.2, 0.3]

    def test_embed_text_api_error(self):
        with patch("index_docs.requests.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = \
                Exception("API error")
            with pytest.raises(Exception):
                embed_text("hello")


# ── Integration via vls.py ───────────────────────────────────────────

class TestIndexSubcommand:
    def test_index_vls_subcommand(self, tmp_path):
        """Verify _index function can be imported and called."""
        from vls import _index
        import argparse
        d = tmp_path / "docs"
        d.mkdir()
        (d / "test.md").write_text("# Hello\nThis is a test document.\n" * 50)
        args = argparse.Namespace(
            paths=[str(d)],
            recursive=True,
            chunk_size=2048,
            chunk_overlap=256,
        )
        _index(args)

    def test_query_no_index(self):
        """Query with no indexed docs returns helpful message."""
        from vls import _query
        import argparse
        args = argparse.Namespace(query="test question", top_k=5, model="llama3.2")
        _query(args)
