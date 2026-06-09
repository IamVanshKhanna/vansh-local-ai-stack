#!/usr/bin/env python3
"""vls - Vansh Local AI Stack CLI

Top-level CLI for the local AI stack. Subcommands:
    scan        Scan filesystems and build a catalog
    classify    Classify files from a catalog
    apply       Apply file move plans safely
    report      Generate disk usage reports
    health      Run system health checks
"""

import argparse
import sys
from pathlib import Path

# Make scripts/ discoverable
sys.path.insert(0, str(Path(__file__).parent / "scripts"))


def _scan(args):
    from scan_drives import scan_directory, format_size, save_dal, save_json
    from db import connection, dal

    paths = [Path(p.strip()) for p in args.paths.split(",")]
    output_path = Path(args.output)
    output_format = args.format or ("dal" if output_path.suffix == ".db" else "json")

    catalog = []
    for path in paths:
        for f in scan_directory(path, args.skip_hidden):
            catalog.append(f)

    if output_format == "json":
        save_json(catalog, output_path)
    else:
        save_dal(catalog, output_path, args.paths, args.skip_hidden)

    print(f"Scanned {len(catalog)} files -> {output_path}")


def _classify(args):
    from classify_files import load_catalog, classify_file, save_dal, save_json, DEFAULT_RULES
    from db import connection, dal

    files, scan_id, source_type = load_catalog(Path(args.input))
    classified = []
    category_counts = {}
    for f in files:
        result = classify_file(f, DEFAULT_RULES, args.use_llm)
        classified.append(result)
        category_counts[result["category"]] = category_counts.get(result["category"], 0) + 1

    output_path = Path(args.output)
    if output_path.suffix == ".db" or source_type == "dal":
        save_dal(classified, output_path, scan_id)
    else:
        save_json(classified, output_path, category_counts)

    print(f"Classified {len(classified)} files -> {output_path}")


def _apply(args):
    from apply_moves import apply_moves
    import json

    with open(args.plan, "r", encoding="utf-8") as f:
        plan = json.load(f)
    moves = plan.get("moves", plan.get("files", []))
    results = apply_moves(
        moves,
        execute=args.execute,
        dry_run=not args.execute,
        force=args.force,
        operation=args.operation,
    )
    print(f"Results: {results['success']} success, {results['failed']} failed, {results['skipped']} skipped")


def _report(args):
    from disk_report import generate_report, format_size
    report = generate_report(args.paths)
    for d in report["drives"]:
        print(f"{d['path']}: {format_size(d['free'] * 1024 ** 3)} free / {format_size(d['total'] * 1024 ** 3)} total")
    if report["alerts"]:
        print("Alerts:", report["alerts"])


def _health(args):
    from health_check import run_health_check
    result = run_health_check(args.checks)
    print(f"Status: {result['status']}")
    for name, check in result["checks"].items():
        print(f"  {name}: {check['status']}")


def main():
    parser = argparse.ArgumentParser(prog="vls")
    sub = parser.add_subparsers(dest="command", required=True)

    # scan
    scan_p = sub.add_parser("scan", help="Scan filesystems")
    scan_p.add_argument("--paths", "-p", required=True)
    scan_p.add_argument("--output", "-o", required=True)
    scan_p.add_argument("--format", "-f", choices=["json", "dal"])
    scan_p.add_argument("--skip-hidden", action="store_true", default=True)
    scan_p.set_defaults(func=_scan)

    # classify
    cls_p = sub.add_parser("classify", help="Classify files")
    cls_p.add_argument("--input", "-i", required=True)
    cls_p.add_argument("--output", "-o", required=True)
    cls_p.add_argument("--use-llm", action="store_true")
    cls_p.set_defaults(func=_classify)

    # apply
    app_p = sub.add_parser("apply", help="Apply move plans")
    app_p.add_argument("--plan", "-p", required=True)
    app_p.add_argument("--execute", action="store_true")
    app_p.add_argument("--force", action="store_true")
    app_p.add_argument("--operation", choices=["move", "copy"], default="move")
    app_p.set_defaults(func=_apply)

    # report
    rep_p = sub.add_parser("report", help="Disk usage report")
    rep_p.add_argument("--paths", nargs="+", default=["/"])
    rep_p.set_defaults(func=_report)

    # health
    hlt_p = sub.add_parser("health", help="Health checks")
    hlt_p.add_argument("--checks", nargs="+", default=["disk", "ram", "ollama", "scripts"])
    hlt_p.set_defaults(func=_health)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
