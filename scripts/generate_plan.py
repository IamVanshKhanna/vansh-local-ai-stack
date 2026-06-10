#!/usr/bin/env python3
"""
generate_plan.py - Generate move plans from classified files

Reads classified file data (JSON or DAL SQLite) and produces a move plan
JSON that can be consumed by ``apply_moves.py``.

Usage:
    python generate_plan.py --input classified.json --targets targets.json --output moves.json
    python generate_plan.py --input classified.json --target-map documents=~/Documents,media=~/Media --output moves.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils import format_size, setup_logger

logger = setup_logger(__name__)

# Default target structure — categories mapped to directories under the user's home
DEFAULT_TARGETS: dict[str, str] = {
    "documents": os.path.expanduser("~/Documents/organized"),
    "media": os.path.expanduser("~/Media/organized"),
    "code": os.path.expanduser("~/Code/organized"),
    "archives": os.path.expanduser("~/Archives/organized"),
    "executables": os.path.expanduser("~/Installers/organized"),
    "data": os.path.expanduser("~/Data/organized"),
    "backups": os.path.expanduser("~/Backups/organized"),
    "downloads": os.path.expanduser("~/Downloads/organized"),
}


# ---------------------------------------------------------------------------
# Loading classified data
# ---------------------------------------------------------------------------

def load_classified(path: Path) -> tuple[list[dict], str]:
    """Load classified files from JSON or DAL SQLite.

    Returns ``(files, source_type)`` where *source_type* is ``"dal"`` or
    ``"json"``.
    """
    if path.suffix == ".db":
        from db import connection, dal

        connection.set_db_path(path)
        scans = dal.list_scans(limit=1)
        if not scans:
            logger.error("No scans found in %s", path)
            sys.exit(1)
        scan_id = scans[0]["id"]
        rows = dal.get_classifications_by_scan(scan_id)
        # Ensure each row has the keys expected by the rest of the pipeline
        files = [
            {
                "id": r.get("file_id"),
                "path": r["path"],
                "name": r["name"],
                "extension": r.get("extension", ""),
                "size": r.get("size", 0),
                "category": r["category"],
                "method": r.get("method", "rule"),
                "confidence": r.get("confidence", 1.0),
            }
            for r in rows
        ]
        return files, "dal"
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("files", data), "json"


def load_targets(path: Optional[Path]) -> dict[str, str]:
    """Load target mapping from a JSON file, or return defaults."""
    if path is None:
        return dict(DEFAULT_TARGETS)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_target_map(target_map_str: str) -> dict[str, str]:
    """Parse ``category=path,category=path`` into a dict."""
    targets: dict[str, str] = {}
    for pair in target_map_str.split(","):
        pair = pair.strip()
        if "=" not in pair:
            continue
        cat, path = pair.split("=", 1)
        targets[cat.strip()] = os.path.expanduser(path.strip())
    return targets


# ---------------------------------------------------------------------------
# Cluster detection
# ---------------------------------------------------------------------------

def detect_existing_clusters(classified_files: list[dict],
                             min_cluster: int = 2) -> list[dict]:
    """Find subfolders containing *min_cluster* or more files.

    Returns a list of ``{"folder": str, "files": int}`` dicts for each
    immediate parent directory where file count meets the threshold.
    """
    from collections import Counter
    parents: list[str] = []
    for f in classified_files:
        p = Path(f.get("path", ""))
        parent = str(p.parent) if p.parent else ""
        if parent:
            parents.append(parent)
    counts = Counter(parents)
    clusters = []
    for folder, cnt in counts.most_common():
        if cnt >= min_cluster:
            clusters.append({"folder": folder, "files": cnt})
    return clusters


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------

def generate_moves(
    classified_files: list[dict],
    targets: dict[str, str],
) -> list[dict]:
    """Create move operations from classified files and target directories.

    Each classified file must have ``path``, ``name``, ``category``, and
    optionally ``size``.  Files whose category has no target entry are
    skipped.
    """
    moves: list[dict] = []

    for f in classified_files:
        category = f.get("category", "uncategorized")
        target_dir = targets.get(category)
        if not target_dir:
            continue

        source = f["path"]
        destination = str(Path(target_dir) / f["name"])

        moves.append(
            {
                "source": source,
                "destination": destination,
                "size": f.get("size", 0),
                "category": category,
            }
        )

    return moves


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a move plan from classified files",
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Classified files file (.json or .db)",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output move plan JSON path",
    )
    parser.add_argument(
        "--targets", "-t",
        help="Target directory mapping JSON file",
    )
    parser.add_argument(
        "--target-map",
        help='Comma-separated category=path pairs, e.g. documents=~/Docs,media=~/Media',
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Load classified files
    classified_path = Path(args.input)
    if not classified_path.exists():
        logger.error("Classified file not found: %s", classified_path)
        sys.exit(1)

    classified_files, source_type = load_classified(classified_path)
    logger.info("Loaded %d classified files (source=%s)", len(classified_files), source_type)

    # Load targets
    if args.target_map:
        targets = parse_target_map(args.target_map)
    else:
        targets = load_targets(Path(args.targets) if args.targets else None)
    logger.info("Using %d target categories", len(targets))

    # Generate moves
    moves = generate_moves(classified_files, targets)
    logger.info("Generated %d move operations", len(moves))

    # Group by category for summary
    category_counts: dict[str, int] = {}
    for m in moves:
        cat = m["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Build plan
    plan = {
        "version": "1.0",
        "generated": datetime.now().isoformat(),
        "source_file": str(classified_path),
        "total_moves": len(moves),
        "category_summary": category_counts,
        "moves": moves,
    }

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    logger.info("Saved move plan to %s", output_path)

    # Print summary
    print(f"\nMove Plan Summary:")
    print(f"  Total moves: {len(moves)}")
    print(f"\n  By category:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")

    if moves:
        total_size = sum(m["size"] for m in moves)
        print(f"\n  Total size: {format_size(total_size)}")
        print(f"\n  Review the plan, then run:")
        print(f"    python apply_moves.py --plan {output_path} --dry-run")
        print(f"    python apply_moves.py --plan {output_path} --execute")


if __name__ == "__main__":
    main()
