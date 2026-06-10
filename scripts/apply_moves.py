#!/usr/bin/env python3
"""
apply_moves.py - Execute file reorganization safely

Applies a move plan to reorganize files. Always runs in dry-run mode first
to preview changes, then requires explicit --execute flag to apply.

Usage:
    python apply_moves.py --plan moves.json --dry-run
    python apply_moves.py --plan moves.json --execute
    python apply_moves.py --plan moves.json --execute --force  # Overwrite existing
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def generate_move_plan(
    classified_files: list[dict],
    target_structure: dict,
    dry_run: bool = True,
) -> list[dict]:
    """Generate move operations from classified files.

    Args:
        classified_files: List of files with categories.
        target_structure: Mapping of category to target directory.
        dry_run: Generate plan without checking conflicts.

    Returns:
        List of move operations.
    """
    moves = []

    for file_data in classified_files:
        source = Path(file_data["path"])
        category = file_data.get("category", "uncategorized")

        # Get target directory for category
        target_dir = target_structure.get(category)
        if not target_dir:
            logger.debug(f"No target for category: {category}")
            continue

        target_path = Path(target_dir) / source.name

        moves.append({
            "source": str(source),
            "destination": str(target_path),
            "size": file_data.get("size", 0),
            "category": category,
        })

    return moves


def validate_moves(moves: list[dict], force: bool = False) -> list[dict]:
    """Validate move operations for conflicts.

    Returns list of issues (empty if all valid).
    """
    issues = []
    destinations = set()

    for move in moves:
        src = Path(move["source"])
        dst = Path(move["destination"])

        # Check source exists
        if not src.exists():
            issues.append({
                "source": str(src),
                "issue": "source_not_found",
                "message": f"Source file not found: {src}",
            })
            continue

        # Check destination parent exists
        if not dst.parent.exists():
            if not force:
                issues.append({
                    "source": str(src),
                    "issue": "destination_parent_missing",
                    "message": f"Destination directory does not exist: {dst.parent}",
                })
                continue

        # Check destination conflict
        if dst.exists() and not force:
            issues.append({
                "source": str(src),
                "issue": "destination_exists",
                "message": f"Destination already exists: {dst}",
            })
            continue

        # Track destinations for duplicate detection
        if str(dst) in destinations:
            issues.append({
                "source": str(src),
                "issue": "duplicate_destination",
                "message": f"Multiple files would move to: {dst}",
            })

        destinations.add(str(dst))

    return issues


def execute_move(
    source: Path,
    destination: Path,
    operation: str = "move",
    force: bool = False,
) -> dict:
    """Execute a file move or copy operation.

    Args:
        source: Source file path.
        destination: Destination file path.
        operation: ``"move"`` or ``"copy"``.
        force: Overwrite existing files.

    Returns:
        Result dictionary with status.
    """
    try:
        # Create destination parent if needed
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Handle existing file
        if destination.exists():
            if force:
                destination.unlink()
            else:
                return {
                    "status": "skipped",
                    "reason": "destination_exists",
                    "path": str(destination),
                }

        # Execute operation
        if operation == "move":
            shutil.move(str(source), str(destination))
        else:  # copy
            shutil.copy2(str(source), str(destination))

        return {
            "status": "success",
            "operation": operation,
            "source": str(source),
            "destination": str(destination),
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "source": str(source),
        }


def apply_moves(
    moves: list[dict],
    execute: bool = False,
    dry_run: bool = False,
    force: bool = False,
    operation: str = "move",
) -> dict:
    """Apply move operations.

    Args:
        moves: List of move operations.
        execute: Actually execute moves.
        dry_run: Just validate and report.
        force: Overwrite existing files.
        operation: ``"move"`` or ``"copy"``.

    Returns:
        Results summary.
    """
    results = {
        "total": len(moves),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "operations": [],
    }

    # Validate first
    issues = validate_moves(moves, force)

    if issues:
        logger.warning(f"Found {len(issues)} validation issues")
        for issue in issues:
            logger.warning(f"  {issue['message']}")
            results["operations"].append({
                "status": "validation_failed",
                **issue,
            })
        results["skipped"] = len(issues)

    # Get valid moves (those without issues)
    issue_sources = {i["source"] for i in issues}
    valid_moves = [m for m in moves if m["source"] not in issue_sources]

    if dry_run:
        logger.info(f"DRY RUN: Would process {len(valid_moves)} moves")
        for move in valid_moves:
            logger.info(f"  {move['source']} -> {move['destination']}")
        return results

    # Execute moves
    if execute:
        for move in valid_moves:
            source = Path(move["source"])
            destination = Path(move["destination"])

            logger.info(f"Moving: {source} -> {destination}")

            result = execute_move(source, destination, operation, force)
            results["operations"].append(result)

            if result["status"] == "success":
                results["success"] += 1
            elif result["status"] == "skipped":
                results["skipped"] += 1
            else:
                results["failed"] += 1

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply file moves safely"
    )
    parser.add_argument(
        "--plan", "-p",
        required=True,
        help="Move plan JSON file"
    )
    parser.add_argument(
        "--output", "-o",
        help="Log output file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without executing (default: True)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute moves (use with caution)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files at destination"
    )
    parser.add_argument(
        "--operation",
        choices=["move", "copy"],
        default="move",
        help="Operation type (default: move)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load move plan
    plan_path = Path(args.plan)
    if not plan_path.exists():
        logger.error(f"Plan file not found: {plan_path}")
        sys.exit(1)

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    moves = plan.get("moves", plan.get("files", []))

    logger.info(f"Loaded {len(moves)} move operations")

    # Safety check
    if args.execute and args.dry_run:
        logger.warning("Both --execute and --dry-run specified. Using --dry-run.")

    # Apply moves
    results = apply_moves(
        moves,
        execute=args.execute,
        dry_run=args.dry_run and not args.execute,
        force=args.force,
        operation=args.operation,
    )

    # Save log
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        log_data = {
            "timestamp": datetime.now().isoformat(),
            "plan_file": str(plan_path),
            "dry_run": args.dry_run and not args.execute,
            "results": results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2)

        logger.info(f"Log saved to {output_path}")

    # Print summary
    print(f"\nMove Results:")
    print(f"  Total operations: {results['total']}")
    print(f"  Successful: {results['success']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Skipped: {results['skipped']}")

    if args.dry_run and not args.execute:
        print(f"\n  This was a DRY RUN. No files were moved.")
        print(f"  Use --execute to apply changes.")


if __name__ == "__main__":
    main()
