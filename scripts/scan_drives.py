#!/usr/bin/env python3
"""
scan_drives.py - Scan and catalog filesystem for analysis

Scans specified directories and records file metadata (path, size, extension,
timestamps) to a JSON or SQLite catalog for further processing.

Usage:
    python scan_drives.py --paths "D:\\,E:\\" --output catalog.json
    python scan_drives.py --paths "/home/user/Documents" --output catalog.db --format sqlite
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Default directories to skip
SKIP_DIRS = {
    # Windows
    "Windows", "Program Files", "Program Files (x86)", "$RECYCLE.BIN",
    "System Volume Information", "pagefile.sys", "hiberfil.sys",
    # macOS
    ".Trash", ".Spotlight-V100", ".fseventsd",
    # Linux
    "proc", "sys", "dev", "run", "tmp",
    # General
    "node_modules", ".git", "__pycache__", ".venv", "venv",
}


def should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    name = path.name.lower()
    return any(skip.lower() == name for skip in SKIP_DIRS)


def scan_directory(root: Path, skip_hidden: bool = True) -> Iterator[dict]:
    """
    Recursively scan directory and yield file metadata.

    Args:
        root: Root directory to scan
        skip_hidden: Skip hidden files and directories

    Yields:
        Dictionary with file metadata
    """
    logger.info(f"Scanning: {root}")

    for path in root.rglob("*"):
        try:
            # Skip hidden files
            if skip_hidden and any(part.startswith(".") for part in path.parts):
                continue

            # Skip directories in skip list
            if path.is_dir() and should_skip(path):
                continue

            # Skip files in skipped directories
            if any(should_skip(Path(part)) for part in path.parts):
                continue

            if path.is_file():
                stat = path.stat()
                yield {
                    "path": str(path),
                    "name": path.name,
                    "extension": path.suffix.lower(),
                    "size": stat.st_size,
                    "size_human": format_size(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat() if hasattr(stat, 'st_ctime') else None,
                    "parent": str(path.parent),
                }

        except PermissionError:
            logger.warning(f"Permission denied: {path}")
        except Exception as e:
            logger.warning(f"Error processing {path}: {e}")


def format_size(size: int) -> str:
    """Format size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def save_json(catalog: list[dict], output_path: Path):
    """Save catalog to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": "1.0",
        "scan_date": datetime.now().isoformat(),
        "total_files": len(catalog),
        "total_size": sum(f["size"] for f in catalog),
        "files": catalog,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved {len(catalog)} files to {output_path}")


def save_sqlite(catalog: list[dict], output_path: Path):
    """Save catalog to SQLite database."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(output_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            name TEXT,
            extension TEXT,
            size INTEGER,
            size_human TEXT,
            modified TEXT,
            created TEXT,
            parent TEXT,
            scan_date TEXT
        )
    """)

    cursor.execute("DELETE FROM files")  # Clear previous scan

    scan_date = datetime.now().isoformat()
    for file_data in catalog:
        cursor.execute("""
            INSERT OR REPLACE INTO files
            (path, name, extension, size, size_human, modified, created, parent, scan_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_data["path"],
            file_data["name"],
            file_data["extension"],
            file_data["size"],
            file_data["size_human"],
            file_data["modified"],
            file_data.get("created"),
            file_data["parent"],
            scan_date,
        ))

    conn.commit()
    conn.close()

    logger.info(f"Saved {len(catalog)} files to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Scan drives and create file catalog"
    )
    parser.add_argument(
        "--paths", "-p",
        required=True,
        help="Comma-separated list of paths to scan (use quotes on Windows)"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output file path (.json or .db)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "sqlite"],
        help="Output format (auto-detected from extension if not specified)"
    )
    parser.add_argument(
        "--skip-hidden",
        action="store_true",
        default=True,
        help="Skip hidden files and directories (default: True)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse paths
    paths = [Path(p.strip()) for p in args.paths.split(",")]

    # Validate paths
    for path in paths:
        if not path.exists():
            logger.error(f"Path does not exist: {path}")
            sys.exit(1)

    # Determine output format
    output_path = Path(args.output)
    output_format = args.format
    if not output_format:
        output_format = "sqlite" if output_path.suffix == ".db" else "json"

    # Scan all paths
    catalog = []
    for path in paths:
        logger.info(f"Starting scan of: {path}")
        for file_data in scan_directory(path, args.skip_hidden):
            catalog.append(file_data)

    # Summary
    total_size = sum(f["size"] for f in catalog)
    logger.info(f"Scan complete: {len(catalog)} files, {format_size(total_size)}")

    # Save catalog
    if output_format == "json":
        save_json(catalog, output_path)
    else:
        save_sqlite(catalog, output_path)

    # Print summary stats
    print(f"\nScan Summary:")
    print(f"  Files scanned: {len(catalog)}")
    print(f"  Total size: {format_size(total_size)}")

    # Extension breakdown
    extensions = {}
    for f in catalog:
        ext = f["extension"] or "(none)"
        extensions[ext] = extensions.get(ext, 0) + 1

    print(f"\nTop 10 extensions:")
    for ext, count in sorted(extensions.items(), key=lambda x: -x[1])[:10]:
        print(f"  {ext}: {count} files")


if __name__ == "__main__":
    main()
