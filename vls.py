"""vls - Vansh Local AI Stack CLI"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

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


def _organize(args: argparse.Namespace) -> None:
    from scan_drives import scan_directory
    from classify_files import classify_file, DEFAULT_RULES
    from generate_plan import generate_moves, DEFAULT_TARGETS
    from apply_moves import apply_moves
    from utils import format_size

    path = Path(args.path)
    if not path.exists():
        print(f"Path not found: {path}")
        sys.exit(1)

    print(f"Scanning {path}...")
    files = list(scan_directory(path))
    print(f"Found {len(files)} files ({format_size(sum(f['size'] for f in files))})")

    print("Classifying files...")
    for f in files:
        classify_file(f, DEFAULT_RULES)

    counts: dict[str, int] = {}
    for f in files:
        cat = f["category"]
        counts[cat] = counts.get(cat, 0) + 1

    print("\nCategory breakdown:")
    for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = (count / len(files)) * 100
        print(f"  {cat}: {count} ({pct:.1f}%)")

    moves = generate_moves(files, DEFAULT_TARGETS)
    if not moves:
        print("Nothing to organize. All files are already categorized.")
        return

    print(f"\nPlan: {len(moves)} files will be moved:")
    for cat in sorted(set(m["category"] for m in moves)):
        cat_moves = [m for m in moves if m["category"] == cat]
        print(f"  {cat}: {len(cat_moves)} files -> {DEFAULT_TARGETS.get(cat, '?')}")
    total = sum(m["size"] for m in moves)
    print(f"Total: {format_size(total)}")

    if args.auto:
        apply = True
    else:
        try:
            resp = input("\nApply this plan? (y/N): ").strip().lower()
            apply = resp == "y"
        except (EOFError, KeyboardInterrupt):
            apply = False

    if apply:
        results = apply_moves(moves, execute=True, force=False, dry_run=False)
        print(f"\nDone: {results['success']} moved, {results['failed']} failed, {results['skipped']} skipped")
    else:
        print("Skipped. Run with --auto to apply without asking.")


def _index(args: argparse.Namespace) -> None:
    from index_docs import index_paths

    missing = [p for p in args.paths if not Path(p).exists()]
    if missing:
        print(f"Paths not found: {', '.join(missing)}")
        sys.exit(1)

    try:
        stats = index_paths(
            paths=args.paths,
            recursive=args.recursive,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        parts = []
        if stats["indexed"]:
            parts.append(f"Indexed {stats['indexed']} files ({stats['total_chunks']} chunks)")
        if stats["skipped"]:
            parts.append(f"{stats['skipped']} skipped (empty or unsupported)")
        if stats["failed"]:
            parts.append(f"{stats['failed']} failed (check logs)")
        print(", ".join(parts) if parts else "No files were indexed")
    except Exception as e:
        print(f"Indexing failed: {e}")
        sys.exit(1)


def _query(args: argparse.Namespace) -> None:
    from rag_query import query

    try:
        result = query(
            query=args.query,
            top_k=args.top_k,
            llm_model=args.model,
        )
        print(f"Answer: {result['answer']}\n")
        if result["sources"]:
            print("Sources:")
            for s in result["sources"]:
                print(f"  [{s['score']:.2f}] {s['name']}")
    except Exception as e:
        print(f"Query failed: {e}")
        sys.exit(1)


def _report(args: argparse.Namespace) -> None:
    from disk_report import get_drive_info, get_all_drives, find_largest_files
    from utils import format_size

    drives = args.paths if args.paths else get_all_drives()
    for drive in drives:
        info = get_drive_info(drive)
        if "error" in info:
            print(f"{drive}: error ({info['error']})")
            continue
        bar_len = 20
        used = int(info["used_percent"] / 100 * bar_len)
        bar = "#" * used + "-" * (bar_len - used)
        print(f" {drive}")
        print(f"   {bar} {info['used_percent']:.0f}%")
        print(f"   {info['free_gb']:.0f} GB free / {info['total_gb']:.0f} GB total")
        if info["status"] != "ok":
            print(f"   ⚠ {info['status'].upper()}: drive is {info['used_percent']:.0f}% full")
        print()

    temp = os.environ.get("TEMP", "")
    if temp and Path(temp).exists():
        try:
            temp_files = list(Path(temp).rglob("*"))
            temp_size = sum(f.stat().st_size for f in temp_files if f.is_file())
            temp_count = sum(1 for f in temp_files if f.is_file())
            print(f"Temp files ({temp}):")
            print(f"   {temp_count} files, {format_size(temp_size)}")
            print()
        except Exception:
            pass

    for folder in [os.environ.get("TEMP", ""), os.path.expanduser("~/Downloads")]:
        if folder and Path(folder).exists():
            try:
                largest = find_largest_files(folder, count=5)
                if largest:
                    print(f"Largest files in {folder}:")
                    for f in largest:
                        print(f"  {f['size_human']:>8}  {f['path']}")
                    print()
            except Exception:
                pass


def _health(args: argparse.Namespace) -> None:
    from health_check import run_health_check
    result = run_health_check(args.checks)
    print(f"Status: {result['status']}")
    for name, check in result["checks"].items():
        print(f"  {name}: {check['status']}")


def _dashboard(args: argparse.Namespace) -> None:
    from dashboard import run_dashboard
    port = args.port
    run_dashboard(port=port)


def _doctor(args: argparse.Namespace) -> None:
    from health_check import check_ollama, check_gpu, check_ram, check_disk, check_scripts
    from examples.notify import notify, notify_email
    from dotenv import load_dotenv

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
        sys.exit(1)


def _ask(args: argparse.Namespace) -> None:
    import requests

    prompt = (
        "You are vls, a local AI CLI tool. The user has asked a question in plain English. "
        "Respond with a JSON object that represents the vls command to run.\n\n"
        "Available commands:\n"
        "  doctor — run full health check\n"
        "  organize <path> — scan, classify, and move files in a folder into organized folders\n"
        "  report — show disk usage with largest files\n"
        "  index <path> — make files in a folder searchable by meaning\n"
        "  query <question> — ask a question about indexed files\n\n"
        "Examples:\n"
        '  "is my system healthy" → {"command": "doctor"}\n'
        '  "clean up my downloads" → {"command": "organize", "path": "~/Downloads"}\n'
        '  "how full is my disk" → {"command": "report"}\n'
        '  "make my papers searchable" → {"command": "index", "path": "~/Papers"}\n'
        '  "find the RAG paper" → {"command": "query", "question": "RAG paper"}\n\n'
        f'User request: "{args.ask}"\n\n'
        "JSON response:"
    )

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False, "options": {"num_predict": 200}},
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["response"].strip()

        # Extract JSON from response
        if "{" in text:
            text = text[text.index("{"):text.rindex("}") + 1]
        cmd = json.loads(text)

        command = cmd.get("command", "")
        if command == "doctor":
            _doctor(argparse.Namespace(checks=None))
        elif command == "report":
            _report(argparse.Namespace(paths=None, include_large_files=True))
        elif command == "organize":
            path = cmd.get("path", ".")
            path = os.path.expanduser(path)
            _organize(argparse.Namespace(path=path, auto=True))
        elif command == "index":
            path = cmd.get("path", ".")
            path = os.path.expanduser(path)
            _index(argparse.Namespace(paths=[path], recursive=True, chunk_size=2048, chunk_overlap=256))
        elif command == "query":
            question = cmd.get("question", args.ask)
            _query(argparse.Namespace(query=question, top_k=5, model="llama3.2"))
        else:
            print(f"I'm not sure how to do that. Try one of these commands:")
            _show_menu()
    except requests.ConnectionError:
        print("Ollama is not running. Start it and try again.")
    except Exception as e:
        print(f"Could not understand request: {e}")
        print("Try: vls doctor, vls report, vls organize <path>, vls index <path>, vls query <question>")


def _show_menu() -> None:
    while True:
        print("")
        print("  +-------------------------------+")
        print("  |   Hermes Local AI Toolkit     |")
        print("  +-------------------------------+")
        print("  |  1. Health check              |")
        print("  |  2. Organize files            |")
        print("  |  3. Disk report               |")
        print("  |  4. Search documents          |")
        print("  |  5. Index new files           |")
        print("  |                               |")
        print("  |  q. Quit                      |")
        print("  +-------------------------------+")
        print("")

        try:
            choice = input("Type a number and press Enter: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("")
            break

        if choice == "1" or choice == "health":
            _doctor(argparse.Namespace(checks=None))
        elif choice == "2" or choice == "organize":
            try:
                p = input("Folder to organize (default: ~/Downloads): ").strip()
                if not p:
                    p = "~/Downloads"
                _organize(argparse.Namespace(path=os.path.expanduser(p), auto=False))
            except (EOFError, KeyboardInterrupt):
                print("")
                continue
        elif choice == "3" or choice == "report":
            _report(argparse.Namespace(paths=None, include_large_files=True))
        elif choice == "4" or choice == "search":
            try:
                q = input("What are you looking for? ").strip()
                if q:
                    _query(argparse.Namespace(query=q, top_k=5, model="llama3.2"))
            except (EOFError, KeyboardInterrupt):
                print("")
                continue
        elif choice == "5" or choice == "index":
            try:
                p = input("Folder or file to index: ").strip()
                if p:
                    _index(argparse.Namespace(paths=[p], recursive=True, chunk_size=2048, chunk_overlap=256))
            except (EOFError, KeyboardInterrupt):
                print("")
                continue
        elif choice == "q" or choice == "quit" or choice == "exit":
            break
        else:
            print("Invalid choice. Type 1-5 or q.")

        print("")
        try:
            input("Press Enter to continue...")
        except (EOFError, KeyboardInterrupt):
            print("")
            break


def main() -> None:
    parser = argparse.ArgumentParser(prog="vls")
    parser.add_argument("--ask", help="Ask in plain English what to do")

    sub = parser.add_subparsers(dest="command")

    scan_p = sub.add_parser("scan", help="Scan files in a folder")
    scan_p.add_argument("--paths", "-p", required=True)
    scan_p.add_argument("--output", "-o", required=True)
    scan_p.add_argument("--format", "-f", choices=["json", "dal"])
    scan_p.add_argument("--skip-hidden", action="store_true", default=True)
    scan_p.set_defaults(func=_scan)

    cls_p = sub.add_parser("classify", help="Categorize files by type")
    cls_p.add_argument("--input", "-i", required=True)
    cls_p.add_argument("--output", "-o", required=True)
    cls_p.add_argument("--use-llm", action="store_true")
    cls_p.set_defaults(func=_classify)

    gen_p = sub.add_parser("generate", help="Plan file moves from classifications")
    gen_p.add_argument("--input", "-i", required=True)
    gen_p.add_argument("--output", "-o", required=True)
    gen_p.add_argument("--targets", "-t")
    gen_p.add_argument("--target-map")
    gen_p.set_defaults(func=_generate)

    app_p = sub.add_parser("apply", help="Execute a move plan")
    app_p.add_argument("--plan", "-p", required=True)
    app_p.add_argument("--execute", action="store_true")
    app_p.add_argument("--force", action="store_true")
    app_p.add_argument("--operation", choices=["move", "copy"], default="move")
    app_p.set_defaults(func=_apply)

    org_p = sub.add_parser("organize", help="Scan, classify, and organize files in one step")
    org_p.add_argument("path", help="Folder to organize (e.g. ~/Downloads)")
    org_p.add_argument("--auto", action="store_true", help="Apply moves without asking")
    org_p.set_defaults(func=_organize)

    idx_p = sub.add_parser("index", help="Make files searchable by meaning")
    idx_p.add_argument("--paths", "-p", nargs="+", required=True)
    idx_p.add_argument("--recursive", action="store_true", default=True)
    idx_p.add_argument("--chunk-size", type=int, default=2048)
    idx_p.add_argument("--chunk-overlap", type=int, default=256)
    idx_p.set_defaults(func=_index)

    qry_p = sub.add_parser("query", help="Ask questions about indexed files")
    qry_p.add_argument("query", help="Your question")
    qry_p.add_argument("--top-k", type=int, default=5)
    qry_p.add_argument("--model", default="llama3.2")
    qry_p.set_defaults(func=_query)

    rep_p = sub.add_parser("report", help="Show disk usage")
    rep_p.add_argument("--paths", nargs="+", default=None)
    rep_p.set_defaults(func=_report)

    hlt_p = sub.add_parser("health", help="Run specific checks")
    hlt_p.add_argument("--checks", nargs="+", default=["disk", "ram", "ollama", "scripts"])
    hlt_p.set_defaults(func=_health)

    doc_p = sub.add_parser("doctor", help="Full system health check")
    doc_p.set_defaults(func=_doctor)

    dash_p = sub.add_parser("dashboard", help="Open local web dashboard")
    dash_p.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    dash_p.set_defaults(func=_dashboard)

    args = parser.parse_args()

    if args.ask:
        _ask(args)
    elif not args.command:
        _show_menu()
    else:
        args.func(args)


if __name__ == "__main__":
    main()
