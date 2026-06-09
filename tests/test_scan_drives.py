"""Tests for scan_drives.py"""

import json
import tempfile
from pathlib import Path

import pytest

# Add scripts directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scan_drives import format_size, should_skip, scan_directory


class TestFormatSize:
    def test_bytes(self):
        assert format_size(500) == "500.0 B"

    def test_kilobytes(self):
        assert format_size(1024) == "1.0 KB"

    def test_megabytes(self):
        assert format_size(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self):
        assert format_size(1024**3) == "1.0 GB"


class TestShouldSkip:
    def test_skip_node_modules(self):
        assert should_skip(Path("node_modules")) is True

    def test_skip_git(self):
        assert should_skip(Path(".git")) is True

    def test_skip_windows(self):
        assert should_skip(Path("Windows")) is True

    def test_allow_normal(self):
        assert should_skip(Path("Documents")) is False

    def test_allow_projects(self):
        assert should_skip(Path("projects")) is False


class TestScanDirectory:
    def test_scan_empty_dir(self, tmp_path):
        results = list(scan_directory(tmp_path, skip_hidden=False))
        assert len(results) == 0

    def test_scan_with_files(self, tmp_path):
        (tmp_path / "test.txt").write_text("hello")
        (tmp_path / "test.py").write_text("print('hi')")

        results = list(scan_directory(tmp_path, skip_hidden=False))
        assert len(results) == 2

        extensions = {r["extension"] for r in results}
        assert ".txt" in extensions
        assert ".py" in extensions

    def test_scan_skips_hidden(self, tmp_path):
        (tmp_path / "visible.txt").write_text("visible")
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "secret.txt").write_text("secret")

        results = list(scan_directory(tmp_path, skip_hidden=True))
        assert len(results) == 1
        assert results[0]["name"] == "visible.txt"

    def test_scan_records_metadata(self, tmp_path):
        (tmp_path / "test.txt").write_text("hello world")

        results = list(scan_directory(tmp_path, skip_hidden=False))
        assert len(results) == 1
        r = results[0]
        assert "path" in r
        assert "size" in r
        assert "extension" in r
        assert "modified" in r
        assert r["extension"] == ".txt"
