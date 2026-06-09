"""Tests for health_check.py"""

import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from health_check import check_ollama, check_ram, check_disk, check_scripts, run_health_check


class TestCheckOllama:
    def test_ollama_not_running(self):
        # Point to a port where nothing runs
        result = check_ollama(host="http://localhost:19999")
        assert result["status"] == "fail"

    def test_ollama_default_host(self):
        # Will pass or fail depending on whether Ollama is running
        result = check_ollama()
        assert result["status"] in ("pass", "fail")


class TestCheckRam:
    def test_ram_check(self):
        result = check_ram()
        # psutil may or may not be installed
        assert result["status"] in ("pass", "warning", "fail")

    def test_ram_check_with_threshold(self):
        result = check_ram(threshold_percent=99)
        # With 99% threshold, should almost always pass
        assert result["status"] in ("pass", "fail")


class TestCheckDisk:
    def test_disk_check(self):
        result = check_disk()
        assert result["status"] in ("pass", "warning", "fail")
        if result["status"] != "fail":
            assert "free_gb" in result


class TestCheckScripts:
    def test_scripts_found(self):
        scripts_dir = str(Path(__file__).parent.parent / "scripts")
        result = check_scripts(scripts_dir)
        assert result["status"] == "pass"
        assert len(result["found"]) >= 5


class TestRunHealthCheck:
    def test_single_check(self):
        result = run_health_check(["disk"])
        assert result["status"] in ("healthy", "degraded", "unhealthy")
        assert "disk" in result["checks"]

    def test_multiple_checks(self):
        result = run_health_check(["disk", "ram", "scripts"])
        assert len(result["checks"]) == 3
