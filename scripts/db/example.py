#!/usr/bin/env python3
"""Example usage of the database data access layer."""

import logging
from pathlib import Path

from db.connection import get_connection, init_db, set_db_path
from db.dal import (
    create_scan,
    update_scan_stats,
    get_scan,
    list_scans,
    insert_files,
    list_files_by_scan,
    count_files_by_scan,
    insert_classifications,
    get_category_summary,
    create_move_plan,
    insert_move_operations,
    get_move_summary,
    update_move_status,
)

logging.basicConfig(level=logging.INFO)


def demo():
    db_path = Path(__file__).parent / "demo.db"
    set_db_path(db_path)
    init_db()

    scan_id = create_scan(
        root_paths="/home/user/Documents", skip_hidden=True, note="demo run"
    )
    print(f"Created scan {scan_id}")

    files = [
        {
            "path": "/home/user/Documents/report.pdf",
            "name": "report.pdf",
            "extension": ".pdf",
            "size": 123456,
            "size_human": "120.6 KB",
            "modified": "2026-06-01T10:00:00",
            "created": "2026-05-01T09:00:00",
            "parent": "/home/user/Documents",
        },
        {
            "path": "/home/user/Documents/notes.txt",
            "name": "notes.txt",
            "extension": ".txt",
            "size": 2048,
            "size_human": "2.0 KB",
            "modified": "2026-06-08T14:00:00",
            "created": "2026-06-08T14:00:00",
            "parent": "/home/user/Documents",
        },
    ]

    insert_files(scan_id, files)
    update_scan_stats(scan_id, file_count=2, total_size=125504)
    print(f"Scan updated: {get_scan(scan_id)}")
    print(f"Files in scan: {count_files_by_scan(scan_id)}")

    classifications = [
        {"file_id": 1, "category": "documents", "method": "extension", "confidence": 1.0},
        {"file_id": 2, "category": "documents", "method": "extension", "confidence": 1.0},
    ]
    insert_classifications(scan_id, classifications)
    print("Category summary:", get_category_summary(scan_id))

    plan_id = create_move_plan(
        scan_id=scan_id,
        target_structure='{"documents": "/home/user/Documents/organized"}',
        note="initial plan",
    )
    print(f"Created move plan {plan_id}")

    operations = [
        {"file_id": 1, "source": files[0]["path"], "destination": "/home/user/Documents/organized/report.pdf", "operation": "move"},
        {"file_id": 2, "source": files[1]["path"], "destination": "/home/user/Documents/organized/notes.txt", "operation": "move"},
    ]
    insert_move_operations(plan_id, operations)
    print(f"Move summary: {get_move_summary(plan_id)}")

    update_move_status(1, "success")
    print(f"Updated move summary: {get_move_summary(plan_id)}")
    print(f"All scans: {list_scans()}")

    print("\nDemo complete. Database:", db_path)


if __name__ == "__main__":
    demo()
