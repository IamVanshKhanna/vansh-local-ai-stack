#!/usr/bin/env python3
"""vls - Vansh Local AI Stack CLI

Top-level CLI for the local AI stack. Subcommands:
    scan        Scan filesystems and build a catalog
    classify    Classify files from a catalog
    generate    Generate move plans from classified files
    apply       Apply file move plans safely
    report      Generate disk usage reports
    health      Run system health checks
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make scripts/ discoverable
sys.path.insert(0, str(Path(__file__).parent / "scripts"))


def _scan(args: argparse.Namespace) -> None:
    from scan_drives import scan_directory, save_dal, save_json

    paths = [Path(p.strip()) for p in args.paths.split(",")]
    output_path = Path(args.output)
    output_format = args.format or ("dal" if output_path.suffix == ".db" else "json")

    catalog: list[dict] = []
    for path in paths:
        for f in scan_directory(path, args.skip_hidden):
            catalog.append(f)

    if output_format == "json":
        save_json(catalog, output_path)
    else:
        save_dal(catalog, output_path, args.paths, args.skip_hidden)

    print(f"Scanned {len(catalog)} files -> {output_path}")


def _classify(args: argparse.Namespace) -> None:
    from classify_files import load_catalog, classify_file, save_dal, save_json, DEFAULT_RULES

    files, scan_id, source_type = load_catalog(Path(args.input))
    classified: list[dict] = []
    category_counts: dict[str, int] = {}
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


def _generate(args: argparse.Namespace) -> None:
    from generate_plan import load_classified, load_targets, parse_target_map, generate_moves
    from utils import format_size
    import json
    from datetime import datetime

    classified_path = Path(args.input)
    classified_files, _source_type = load_classified(classified_path)

    if args.target_map:
        targets = parse_target_map(args.target_map)
    else:
        targets = load_targets(Path(args.targets) if args.targets else None)

    moves = generate_moves(classified_files, targets)

    category_counts: dict[str, int] = {}
    for m in moves:
        cat = m["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    plan = {
        "version": "1.0",
        "generated": datetime.now().isoformat(),
        "source_file": str(classified_path),
        "total_moves": len(moves),
        "category_summary": category_counts,
        "moves": moves,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    print(f"Generated {len(moves)} move operations -> {output_path}")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


def _apply(args: argparse.Namespace) -> None:
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


def _index(args: argparse.Namespace) -> None:
    from index_docs import index_paths

    stats = index_paths(
        paths=args.paths,
        recursive=args.recursive,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    print(f"Indexed {stats['indexed']} files ({stats['total_chunks']} chunks), "
          f"{stats['skipped']} skipped, {stats['failed']} failed")


def _query(args: argparse.Namespace) -> None:
    from rag_query import query

    result = query(
        query=args.query,
        top_k=args.top_k,
        llm_model=args.model,
    )
    print(f"\nAnswer: {result['answer']}\n")
    if result["sources"]:
        print("Sources:")
        for s in result["sources"]:
            print(f"  [{s['score']:.2f}] {s['name']}")


def _report(args: argparse.Namespace) -> None:
    from disk_report import generate_report
    from utils import format_size

    report = generate_report(args.paths)
    for d in report["drives"]:
        print(f"{d['path']}: {d['free_gb']} GB free / {d['total_gb']} GB total")
    if report["alerts"]:
        print("Alerts:", report["alerts"])


def _health(args: argparse.Namespace) -> None:
    from health_check import run_health_check
    result = run_health_check(args.checks)
    print(f"Status: {result['status']}")
    for name, check in result["checks"].items():
        print(f"  {name}: {check['status']}")


def _doctor(args: argparse.Namespace) -> None:
    """Run all health checks and print a clear summary."""
    from health_check import check_ollama, check_gpu, check_ram, check_disk, check_scripts
    from examples.notify import notify, notify_email
    from dotenv import load_dotenv
    import os

    load_dotenv()

    checks = {
        "ollama": check_ollama(),
        "gpu": check_gpu(),
        "ram": check_ram(),
        "disk": check_disk(),
        "scripts": check_scripts(),
    }

    all_ok = True
    alerts = []
    for name, result in checks.items():
        status = result.get("status", "fail")
        symbol = {"pass": "PASS", "warning": "WARN", "fail": "FAIL"}.get(status, "???")
        detail = ""
        if name == "ollama" and status == "pass":
            detail = f" ({result['models_available']} models loaded)"
        elif name == "gpu" and status == "pass":
            gpu = result.get("gpus", [{}])[0]
            detail = f" - {gpu.get('name', 'N/A')} ({gpu.get('memory_free', '?')} free)"
        elif name == "ram" and status == "pass":
            detail = f" ({result.get('available_gb', '?')} GB available)"
        elif name == "disk" and status == "pass":
            detail = f" ({result.get('free_gb', '?')} GB free)"
        elif status == "fail":
            all_ok = False
            detail = f" - {result.get('error', result.get('note', 'unknown error'))}"
            alerts.append(f"{name}: {result.get('error', result.get('note', 'failed'))}")
        elif status == "warning":
            all_ok = False
            detail = f" - {result.get('error', result.get('alert', result.get('note', 'warning')))}"
            alerts.append(f"{name}: {result.get('alert', result.get('note', 'warning'))}")

        print(f"  [{symbol}] {name}{detail}")

    if not all_ok:
        msg = "; ".join(alerts)
        notify("vls doctor - issues found", msg)
        smtp_server = os.getenv("EMAIL_SMTP_SERVER")
        if smtp_server:
            notify_email("vls doctor alert", msg)

    print("")
    if all_ok:
        print("  All checks passed -- system is healthy")
    else:
        print("  Some checks need attention -- review warnings above")
        exit(1)


def main() -> None:
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

    # generate
    gen_p = sub.add_parser("generate", help="Generate move plans from classified files")
    gen_p.add_argument("--input", "-i", required=True, help="Classified files (.json or .db)")
    gen_p.add_argument("--output", "-o", required=True, help="Output move plan JSON")
    gen_p.add_argument("--targets", "-t", help="Target directory mapping JSON file")
    gen_p.add_argument("--target-map", help="Comma-separated category=path pairs")
    gen_p.set_defaults(func=_generate)

    # apply
    app_p = sub.add_parser("apply", help="Apply move plans")
    app_p.add_argument("--plan", "-p", required=True)
    app_p.add_argument("--execute", action="store_true")
    app_p.add_argument("--force", action="store_true")
    app_p.add_argument("--operation", choices=["move", "copy"], default="move")
    app_p.set_defaults(func=_apply)

    # index
    idx_p = sub.add_parser("index", help="Index documents for RAG search")
    idx_p.add_argument("--paths", "-p", nargs="+", required=True,
                       help="Files or directories to index")
    idx_p.add_argument("--recursive", action="store_true", default=True)
    idx_p.add_argument("--chunk-size", type=int, default=2048,
                       help="Character chunk size (default: 2048)")
    idx_p.add_argument("--chunk-overlap", type=int, default=256,
                       help="Character overlap between chunks (default: 256)")
    idx_p.set_defaults(func=_index)

    # query
    qry_p = sub.add_parser("query", help="Ask questions about indexed documents")
    qry_p.add_argument("query", help="Natural language question")
    qry_p.add_argument("--top-k", type=int, default=5,
                       help="Number of context chunks (default: 5)")
    qry_p.add_argument("--model", default="llama3.2",
                       help="LLM model for answering (default: llama3.2)")
    qry_p.set_defaults(func=_query)

    # report
    rep_p = sub.add_parser("report", help="Disk usage report")
    rep_p.add_argument("--paths", nargs="+", default=["/"])
    rep_p.set_defaults(func=_report)

    # health
    hlt_p = sub.add_parser("health", help="Run specific health checks")
    hlt_p.add_argument("--checks", nargs="+", default=["disk", "ram", "ollama", "scripts"])
    hlt_p.set_defaults(func=_health)

    # doctor
    doc_p = sub.add_parser("doctor", help="Full system health summary")
    doc_p.set_defaults(func=_doctor)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
