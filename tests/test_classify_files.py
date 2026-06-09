"""Tests for classify_files.py"""

import json
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from classify_files import (
    classify_by_extension,
    classify_by_path,
    classify_file,
    DEFAULT_RULES,
)


class TestClassifyByExtension:
    def test_pdf(self):
        result = classify_by_extension({"extension": ".pdf"}, DEFAULT_RULES)
        assert result == "documents"

    def test_python(self):
        result = classify_by_extension({"extension": ".py"}, DEFAULT_RULES)
        assert result == "code"

    def test_mp4(self):
        result = classify_by_extension({"extension": ".mp4"}, DEFAULT_RULES)
        assert result == "media"

    def test_zip(self):
        result = classify_by_extension({"extension": ".zip"}, DEFAULT_RULES)
        assert result == "archives"

    def test_exe(self):
        result = classify_by_extension({"extension": ".exe"}, DEFAULT_RULES)
        assert result == "executables"

    def test_csv(self):
        result = classify_by_extension({"extension": ".csv"}, DEFAULT_RULES)
        assert result == "data"

    def test_bak(self):
        result = classify_by_extension({"extension": ".bak"}, DEFAULT_RULES)
        assert result == "backups"

    def test_unknown(self):
        result = classify_by_extension({"extension": ".xyz123"}, DEFAULT_RULES)
        assert result is None


class TestClassifyByPath:
    def test_documents_dir(self):
        result = classify_by_path(
            {"path": "/home/user/Documents/report.pdf"}, DEFAULT_RULES
        )
        assert result == "documents"

    def test_downloads_dir(self):
        result = classify_by_path(
            {"path": "/home/user/Downloads/setup.exe"}, DEFAULT_RULES
        )
        assert result == "downloads"

    def test_projects_dir(self):
        result = classify_by_path(
            {"path": "/home/user/projects/myapp/main.py"}, DEFAULT_RULES
        )
        assert result == "code"

    def test_windows_dir(self):
        result = classify_by_path(
            {"path": "C:\\Windows\\System32\\driver.sys"}, DEFAULT_RULES
        )
        assert result == "system"

    def test_no_match(self):
        result = classify_by_path(
            {"path": "/home/user/misc/file.xyz"}, DEFAULT_RULES
        )
        assert result is None


class TestClassifyFile:
    def test_extension_takes_priority(self):
        file_data = {"extension": ".pdf", "path": "/home/user/Downloads/report.pdf"}
        result = classify_file(file_data, DEFAULT_RULES)
        assert result["category"] == "documents"

    def test_path_fallback(self):
        file_data = {"extension": ".xyz", "path": "/home/user/Documents/unknown.xyz"}
        result = classify_file(file_data, DEFAULT_RULES)
        # Path-based should match "documents"
        assert result["category"] == "documents"

    def test_default_category(self):
        file_data = {"extension": ".xyz", "path": "/home/user/misc/unknown.xyz"}
        result = classify_file(file_data, DEFAULT_RULES)
        assert result["category"] == "uncategorized"
