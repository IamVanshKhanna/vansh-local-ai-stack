"""Data access layer for scans, files, classifications, and moves."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .connection import get_connection

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────────
# Scans
# ───────────────────────────────────────────────────────────────────────────

def create_scan(root_paths: str, skip_hidden: bool = True, note: str = "") -> int:
    """Start a new scan and return its ID."""
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO scans (root_paths, skip_hidden, status, note)
               VALUES (?, ?, 'in_progress', ?)""",
            (root_paths, int(skip_hidden), note),
        )
        conn.commit()
        scan_id = cursor.lastrowid
    logger.info("Created scan %s for %s", scan_id, root_paths)
    return scan_id


def update_scan_stats(scan_id: int, file_count: int, total_size: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE scans
               SET file_count = ?, total_size = ?, status = 'completed'
               WHERE id = ?""",
            (file_count, total_size, scan_id),
        )
        conn.commit()


def get_scan(scan_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM scans WHERE id = ?", (scan_id,)
        ).fetchone()
    return dict(row) if row else None


def list_scans(limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM scans ORDER BY scan_date DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ───────────────────────────────────────────────────────────────────────────
# Files
# ───────────────────────────────────────────────────────────────────────────

def insert_files(scan_id: int, files: list[dict]) -> None:
    """Bulk-insert file metadata under a scan."""
    if not files:
        return
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO files
               (scan_id, path, name, extension, size, size_human, modified, created, parent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    scan_id,
                    f["path"],
                    f["name"],
                    f.get("extension", ""),
                    f["size"],
                    f.get("size_human", ""),
                    f.get("modified"),
                    f.get("created"),
                    f.get("parent", ""),
                )
                for f in files
            ],
        )
        conn.commit()
    logger.info("Inserted %s files for scan %s", len(files), scan_id)


def list_files_by_scan(scan_id: int, limit: int = 1000) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM files WHERE scan_id = ? LIMIT ?", (scan_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def count_files_by_scan(scan_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM files WHERE scan_id = ?", (scan_id,)
        ).fetchone()
    return row[0] if row else 0


def get_file(file_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    return dict(row) if row else None


# ───────────────────────────────────────────────────────────────────────────
# Classifications
# ───────────────────────────────────────────────────────────────────────────

def insert_classifications(
    scan_id: int, classifications: list[dict]
) -> None:
    """Bulk-insert classification results.

    Each dict must contain: file_id, category, method, confidence.
    """
    if not classifications:
        return
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO classifications
               (scan_id, file_id, category, method, confidence)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (
                    scan_id,
                    c["file_id"],
                    c["category"],
                    c.get("method", "rule"),
                    c.get("confidence", 1.0),
                )
                for c in classifications
            ],
        )
        conn.commit()
    logger.info("Inserted %s classifications for scan %s", len(classifications), scan_id)


def get_classifications_by_scan(scan_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT c.*, f.path, f.name, f.extension
               FROM classifications c
               JOIN files f ON c.file_id = f.id
               WHERE c.scan_id = ?""",
            (scan_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_category_summary(scan_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT category, COUNT(*) as count,
                  SUM(f.size) as total_size
               FROM classifications c
               JOIN files f ON c.file_id = f.id
               WHERE c.scan_id = ?
               GROUP BY category""",
            (scan_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ───────────────────────────────────────────────────────────────────────────
# Move Plans
# ───────────────────────────────────────────────────────────────────────────

def create_move_plan(scan_id: int, target_structure: str, note: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO move_plans (scan_id, target_structure, note)
               VALUES (?, ?, ?)""",
            (scan_id, target_structure, note),
        )
        conn.commit()
        plan_id = cursor.lastrowid
    logger.info("Created move plan %s for scan %s", plan_id, scan_id)
    return plan_id


def update_move_plan_status(plan_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE move_plans SET status = ? WHERE id = ?", (status, plan_id)
        )
        conn.commit()


def get_move_plan(plan_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM move_plans WHERE id = ?", (plan_id,)).fetchone()
    return dict(row) if row else None


def list_move_plans(scan_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM move_plans WHERE scan_id = ? ORDER BY created_at DESC",
            (scan_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ───────────────────────────────────────────────────────────────────────────
# Move Operations
# ───────────────────────────────────────────────────────────────────────────

def insert_move_operations(plan_id: int, operations: list[dict]) -> None:
    """Bulk-insert move operations.

    Each dict must contain: file_id, source, destination, operation.
    """
    if not operations:
        return
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO move_operations
               (plan_id, file_id, source, destination, operation)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (
                    plan_id,
                    o["file_id"],
                    o["source"],
                    o["destination"],
                    o.get("operation", "move"),
                )
                for o in operations
            ],
        )
        conn.commit()
    logger.info("Inserted %s move operations for plan %s", len(operations), plan_id)


def get_move_operations(plan_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT mo.*, f.name, f.size
               FROM move_operations mo
               JOIN files f ON mo.file_id = f.id
               WHERE mo.plan_id = ?""",
            (plan_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_move_status(move_id: int, status: str, error: str = "") -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE move_operations
               SET status = ?, executed_at = ?, error = ?
               WHERE id = ?""",
            (status, datetime.now().isoformat(), error, move_id),
        )
        conn.commit()


def get_move_summary(plan_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT status, COUNT(*) as count
               FROM move_operations
               WHERE plan_id = ?
               GROUP BY status""",
            (plan_id,),
        ).fetchall()
    summary = {r["status"]: r["count"] for r in row}
    return summary
