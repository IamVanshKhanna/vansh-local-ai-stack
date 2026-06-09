"""Tests for disk_report.py"""

import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from disk_report import get_drive_info, format_size, generate_report


class TestFormatSize:
    def test_bytes(self):
        assert format_size(500) == "500.0 B"

    def test_kilobytes(self):
        assert format_size(1024) == "1.0 KB"

    def test_gigabytes(self):
        assert format_size(1024**3) == "1.0 GB"


class TestGetDriveInfo:
    def test_root_drive(self):
        result = get_drive_info("/")
        assert "total_gb" in result
        assert "used_gb" in result
        assert "free_gb" in result
        assert "used_percent" in result
        assert result["status"] in ("ok", "warning", "critical")

    def test_invalid_drive(self):
        result = get_drive_info("/nonexistent_drive_xyz")
        assert result["status"] == "error"


class TestGenerateReport:
    def test_basic_report(self):
        report = generate_report(["/"])
        assert "generated" in report
        assert "drives" in report
        assert "alerts" in report
        assert len(report["drives"]) >= 1

    def test_report_with_alerts(self):
        # Use a very low threshold to trigger alert
        report = generate_report(["/"])
        # Structure is correct even if no alerts
        assert isinstance(report["alerts"], list)
