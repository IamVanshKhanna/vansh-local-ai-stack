"""Shared utilities for vansh-local-ai-stack scripts."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


def format_size(size: int) -> str:
    """Format size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def setup_logger(
    name: str,
    level: int = logging.INFO,
    verbose: bool = False,
) -> logging.Logger:
    """Set up a logger with consistent formatting.

    Args:
        name: Logger name (usually ``__name__``).
        level: Base logging level.
        verbose: If True, force DEBUG level regardless of *level*.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    if verbose:
        level = logging.DEBUG
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        fmt = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    return logger


def project_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parent.parent


def scripts_dir() -> Path:
    """Return the scripts directory."""
    return Path(__file__).resolve().parent
