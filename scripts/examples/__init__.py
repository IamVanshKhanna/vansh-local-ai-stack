"""
Helper scripts for the local AI stack.

This module provides utility functions used by the main scripts.
"""

from .logger import setup_logger, StructuredLogger, log_execution_time
from .notify import notify, notify_email, notify_if_alert

__all__ = [
    "setup_logger",
    "StructuredLogger",
    "log_execution_time",
    "notify",
    "notify_email",
    "notify_if_alert",
]
