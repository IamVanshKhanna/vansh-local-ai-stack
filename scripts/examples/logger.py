"""
Logging utilities for local AI stack scripts.

Provides consistent logging configuration and formatters.

Usage:
    from examples.logger import setup_logger

    logger = setup_logger(__name__)
    logger.info("Starting operation")
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
) -> logging.Logger:
    """
    Set up a logger with consistent formatting.

    Args:
        name: Logger name (usually __name__)
        level: Logging level
        log_file: Optional log file name
        log_dir: Directory for log files

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        if log_dir:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            log_file = log_path / log_file

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


def log_execution_time(logger: logging.Logger, operation: str):
    """
    Decorator to log execution time of a function.

    Usage:
        @log_execution_time(logger, "scan operation")
        def scan_files():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = datetime.now()
            logger.info(f"Starting {operation}")

            try:
                result = func(*args, **kwargs)
                elapsed = (datetime.now() - start).total_seconds()
                logger.info(f"Completed {operation} in {elapsed:.2f}s")
                return result

            except Exception as e:
                elapsed = (datetime.now() - start).total_seconds()
                logger.error(f"Failed {operation} after {elapsed:.2f}s: {e}")
                raise

        return wrapper
    return decorator


class StructuredLogger:
    """Logger that outputs structured JSON logs."""

    def __init__(self, name: str, log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.log_file = log_file

        if log_file:
            handler = logging.FileHandler(log_file)
            self.logger.addHandler(handler)

    def log(self, level: str, event: str, **kwargs):
        """Log a structured event."""
        import json

        record = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "event": event,
            **kwargs
        }

        message = json.dumps(record)

        if level == "DEBUG":
            self.logger.debug(message)
        elif level == "INFO":
            self.logger.info(message)
        elif level == "WARNING":
            self.logger.warning(message)
        elif level == "ERROR":
            self.logger.error(message)
        elif level == "CRITICAL":
            self.logger.critical(message)

    def info(self, event: str, **kwargs):
        self.log("INFO", event, **kwargs)

    def warning(self, event: str, **kwargs):
        self.log("WARNING", event, **kwargs)

    def error(self, event: str, **kwargs):
        self.log("ERROR", event, **kwargs)
