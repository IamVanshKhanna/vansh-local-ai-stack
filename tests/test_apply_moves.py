"""Tests for apply_moves.py"""

import json
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from apply_moves import validate_moves, execute_move, generate_move_plan


class TestValidateMoves:
    def test_valid_move(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("content")
        dst = tmp_path / "dest.txt"

        moves = [{"source": str(src), "destination": str(dst), "size": 7}]
        issues = validate_moves(moves)
        assert len(issues) == 0

    def test_source_not_found(self, tmp_path):
        moves = [{"source": "/nonexistent/file.txt", "destination": str(tmp_path / "out.txt"), "size": 0}]
        issues = validate_moves(moves)
        assert len(issues) == 1
        assert issues[0]["issue"] == "source_not_found"

    def test_destination_exists_no_force(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("content")
        dst = tmp_path / "dest.txt"
        dst.write_text("existing")

        moves = [{"source": str(src), "destination": str(dst), "size": 7}]
        issues = validate_moves(moves, force=False)
        assert len(issues) == 1
        assert issues[0]["issue"] == "destination_exists"

    def test_destination_exists_with_force(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("content")
        dst = tmp_path / "dest.txt"
        dst.write_text("existing")

        moves = [{"source": str(src), "destination": str(dst), "size": 7}]
        issues = validate_moves(moves, force=True)
        assert len(issues) == 0


class TestExecuteMove:
    def test_move_success(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("hello")
        dst = tmp_path / "dest.txt"

        result = execute_move(src, dst, operation="move")
        assert result["status"] == "success"
        assert dst.exists()
        assert not src.exists()

    def test_copy_success(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("hello")
        dst = tmp_path / "dest.txt"

        result = execute_move(src, dst, operation="copy")
        assert result["status"] == "success"
        assert dst.exists()
        assert src.exists()

    def test_move_creates_parent(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("hello")
        dst = tmp_path / "subdir" / "nested" / "dest.txt"

        result = execute_move(src, dst, operation="move")
        assert result["status"] == "success"
        assert dst.exists()

    def test_move_destination_exists_no_force(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("hello")
        dst = tmp_path / "dest.txt"
        dst.write_text("existing")

        result = execute_move(src, dst, operation="move", force=False)
        assert result["status"] == "skipped"
        assert dst.read_text() == "existing"


class TestGenerateMovePlan:
    def test_generates_moves(self):
        files = [
            {"path": "/home/user/Downloads/report.pdf", "name": "report.pdf", "category": "documents"},
            {"path": "/home/user/Downloads/photo.jpg", "name": "photo.jpg", "category": "media"},
        ]
        targets = {
            "documents": "/home/user/Organized/Documents",
            "media": "/home/user/Organized/Media",
        }

        moves = generate_move_plan(files, targets)
        assert len(moves) == 2
        assert Path(moves[0]["destination"]) == Path("/home/user/Organized/Documents/report.pdf")
        assert Path(moves[1]["destination"]) == Path("/home/user/Organized/Media/photo.jpg")

    def test_skips_unknown_category(self):
        files = [
            {"path": "/home/user/Downloads/file.xyz", "name": "file.xyz", "category": "uncategorized"},
        ]
        targets = {"documents": "/home/user/Organized/Documents"}

        moves = generate_move_plan(files, targets)
        assert len(moves) == 0
