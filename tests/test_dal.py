"""Tests for the db data access layer."""

import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from db.connection import get_connection, init_db, set_db_path
from db.dal import (
    create_scan,
    update_scan_stats,
    get_scan,
    list_scans,
    insert_files,
    list_files_by_scan,
    count_files_by_scan,
    get_file,
    insert_classifications,
    get_classifications_by_scan,
    get_category_summary,
    create_move_plan,
    update_move_plan_status,
    get_move_plan,
    list_move_plans,
    insert_move_operations,
    get_move_operations,
    get_move_summary,
    update_move_status,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Provide a fresh database per test."""
    db_path = tmp_path / "test.db"
    set_db_path(db_path)
    init_db()
    yield
    set_db_path(Path(__file__).parent.parent / "scripts" / "db" / "catalog.db")


class TestScans:
    def test_create_scan(self):
        scan_id = create_scan("/tmp", skip_hidden=True, note="test")
        assert scan_id == 1
        scan = get_scan(scan_id)
        assert scan["root_paths"] == "/tmp"
        assert scan["status"] == "in_progress"

    def test_update_scan_stats(self):
        scan_id = create_scan("/tmp")
        update_scan_stats(scan_id, 42, 1024)
        scan = get_scan(scan_id)
        assert scan["file_count"] == 42
        assert scan["total_size"] == 1024
        assert scan["status"] == "completed"

    def test_list_scans(self):
        create_scan("/a")
        create_scan("/b")
        scans = list_scans(limit=10)
        assert len(scans) == 2
        assert scans[0]["root_paths"] == "/b"


class TestFiles:
    def test_insert_and_list(self):
        scan_id = create_scan("/tmp")
        files = [
            {"path": "/tmp/a.txt", "name": "a.txt", "extension": ".txt", "size": 100, "size_human": "100 B", "modified": "2026-06-01T00:00:00", "created": "2026-06-01T00:00:00", "parent": "/tmp"},
            {"path": "/tmp/b.jpg", "name": "b.jpg", "extension": ".jpg", "size": 2048, "size_human": "2.0 KB", "modified": "2026-06-02T00:00:00", "created": "2026-06-02T00:00:00", "parent": "/tmp"},
        ]
        insert_files(scan_id, files)
        assert count_files_by_scan(scan_id) == 2
        rows = list_files_by_scan(scan_id)
        assert {r["name"] for r in rows} == {"a.txt", "b.jpg"}

    def test_get_file(self):
        scan_id = create_scan("/tmp")
        files = [
            {"path": "/tmp/a.txt", "name": "a.txt", "extension": ".txt", "size": 100, "size_human": "100 B", "modified": "2026-06-01T00:00:00", "created": "2026-06-01T00:00:00", "parent": "/tmp"},
        ]
        insert_files(scan_id, files)
        row = get_file(1)
        assert row["name"] == "a.txt"

    def test_empty_insert(self):
        scan_id = create_scan("/tmp")
        insert_files(scan_id, [])
        assert count_files_by_scan(scan_id) == 0


class TestClassifications:
    def test_insert_and_summary(self):
        scan_id = create_scan("/tmp")
        files = [
            {"path": "/tmp/a.txt", "name": "a.txt", "extension": ".txt", "size": 100, "size_human": "100 B", "modified": "2026-06-01T00:00:00", "created": "2026-06-01T00:00:00", "parent": "/tmp"},
            {"path": "/tmp/b.jpg", "name": "b.jpg", "extension": ".jpg", "size": 2048, "size_human": "2.0 KB", "modified": "2026-06-02T00:00:00", "created": "2026-06-02T00:00:00", "parent": "/tmp"},
        ]
        insert_files(scan_id, files)
        classifications = [
            {"file_id": 1, "category": "documents", "method": "extension", "confidence": 1.0},
            {"file_id": 2, "category": "media", "method": "extension", "confidence": 0.9},
        ]
        insert_classifications(scan_id, classifications)
        summary = get_category_summary(scan_id)
        assert len(summary) == 2
        docs = next(s for s in summary if s["category"] == "documents")
        assert docs["count"] == 1
        assert docs["total_size"] == 100

    def test_get_classifications(self):
        scan_id = create_scan("/tmp")
        files = [
            {"path": "/tmp/a.txt", "name": "a.txt", "extension": ".txt", "size": 100, "size_human": "100 B", "modified": "2026-06-01T00:00:00", "created": "2026-06-01T00:00:00", "parent": "/tmp"},
        ]
        insert_files(scan_id, files)
        insert_classifications(scan_id, [
            {"file_id": 1, "category": "documents", "method": "extension", "confidence": 1.0},
        ])
        rows = get_classifications_by_scan(scan_id)
        assert len(rows) == 1
        assert rows[0]["category"] == "documents"
        assert rows[0]["name"] == "a.txt"


class TestMovePlans:
    def test_create_and_list(self):
        scan_id = create_scan("/tmp")
        plan_id = create_move_plan(scan_id, '{"documents": "/tmp/organized"}', "note")
        assert plan_id == 1
        plan = get_move_plan(plan_id)
        assert plan["target_structure"] == '{"documents": "/tmp/organized"}'
        assert plan["status"] == "draft"
        assert len(list_move_plans(scan_id)) == 1

    def test_update_status(self):
        scan_id = create_scan("/tmp")
        plan_id = create_move_plan(scan_id, "{}")
        update_move_plan_status(plan_id, "approved")
        assert get_move_plan(plan_id)["status"] == "approved"


class TestMoveOperations:
    def test_insert_and_summary(self):
        scan_id = create_scan("/tmp")
        files = [
            {"path": "/tmp/a.txt", "name": "a.txt", "extension": ".txt", "size": 100, "size_human": "100 B", "modified": "2026-06-01T00:00:00", "created": "2026-06-01T00:00:00", "parent": "/tmp"},
            {"path": "/tmp/b.jpg", "name": "b.jpg", "extension": ".jpg", "size": 2048, "size_human": "2.0 KB", "modified": "2026-06-02T00:00:00", "created": "2026-06-02T00:00:00", "parent": "/tmp"},
        ]
        insert_files(scan_id, files)
        plan_id = create_move_plan(scan_id, "{}")
        operations = [
            {"file_id": 1, "source": "/tmp/a.txt", "destination": "/tmp/organized/a.txt", "operation": "move"},
            {"file_id": 2, "source": "/tmp/b.jpg", "destination": "/tmp/organized/b.jpg", "operation": "move"},
        ]
        insert_move_operations(plan_id, operations)
        summary = get_move_summary(plan_id)
        assert summary == {"pending": 2}

    def test_update_status(self):
        scan_id = create_scan("/tmp")
        files = [
            {"path": "/tmp/a.txt", "name": "a.txt", "extension": ".txt", "size": 100, "size_human": "100 B", "modified": "2026-06-01T00:00:00", "created": "2026-06-01T00:00:00", "parent": "/tmp"},
        ]
        insert_files(scan_id, files)
        plan_id = create_move_plan(scan_id, "{}")
        insert_move_operations(plan_id, [
            {"file_id": 1, "source": "/tmp/a.txt", "destination": "/tmp/organized/a.txt", "operation": "move"},
        ])
        update_move_status(1, "success")
        summary = get_move_summary(plan_id)
        assert summary == {"success": 1}

    def test_get_operations(self):
        scan_id = create_scan("/tmp")
        files = [
            {"path": "/tmp/a.txt", "name": "a.txt", "extension": ".txt", "size": 100, "size_human": "100 B", "modified": "2026-06-01T00:00:00", "created": "2026-06-01T00:00:00", "parent": "/tmp"},
        ]
        insert_files(scan_id, files)
        plan_id = create_move_plan(scan_id, "{}")
        insert_move_operations(plan_id, [
            {"file_id": 1, "source": "/tmp/a.txt", "destination": "/tmp/organized/a.txt", "operation": "move"},
        ])
        rows = get_move_operations(plan_id)
        assert len(rows) == 1
        assert rows[0]["name"] == "a.txt"
