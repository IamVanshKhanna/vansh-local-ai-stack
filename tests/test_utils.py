import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from utils import format_size, setup_logger

import pytest


# ── format_size ─────────────────────────────────────────────────────────

def test_format_size_bytes():
    assert format_size(0) == "0.0 B"
    assert format_size(512) == "512.0 B"


def test_format_size_kb():
    assert format_size(1024) == "1.0 KB"
    assert format_size(1536) == "1.5 KB"


def test_format_size_mb():
    assert format_size(1024 * 1024) == "1.0 MB"
    assert format_size(1024 * 1024 * 2.5) == "2.5 MB"


def test_format_size_gb():
    assert format_size(1024 ** 3) == "1.0 GB"


def test_format_size_tb():
    assert format_size(1024 ** 4) == "1.0 TB"


# ── setup_logger ────────────────────────────────────────────────────────

def test_setup_logger_returns_logger_with_default_level():
    logger = setup_logger("test_default")
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.INFO


def test_setup_logger_verbose_sets_debug():
    logger = setup_logger("test_verbose", verbose=True)
    assert logger.level == logging.DEBUG


def test_setup_logger_custom_level():
    logger = setup_logger("test_custom", level=logging.WARNING)
    assert logger.level == logging.WARNING


def test_setup_logger_has_handler():
    logger = setup_logger("test_handler")
    assert len(logger.handlers) >= 1
