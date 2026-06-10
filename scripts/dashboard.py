"""vls dashboard — local web UI with system resource monitor."""

from __future__ import annotations

import json
import os
import socket
import sys
import webbrowser
from pathlib import Path
from threading import Timer

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="Hermes Dashboard")

TEMPLATES = Path(__file__).parent / "templates"
_last_moves: list[dict] = []


@app.get("/api/resources")
def api_resources():
    from resource_monitor import get_resources
    return JSONResponse(get_resources())


@app.get("/api/doctor")
def api_doctor():
    from health_check import check_ollama, check_gpu, check_ram, check_disk, check_scripts
    checks = {
        "ollama": check_ollama(),
        "gpu": check_gpu(),
        "ram": check_ram(),
        "disk": check_disk(),
        "scripts": check_scripts(),
    }
    all_ok = all(c.get("status") == "pass" for c in checks.values())
    return JSONResponse({"all_ok": all_ok, "checks": checks})


@app.get("/api/report")
def api_report():
    from disk_report import get_drive_info, get_all_drives, find_largest_files
    drives = get_all_drives()
    result = {"drives": [], "temp": None, "largest": {}}
    for d in drives:
        info = get_drive_info(d)
        if "error" not in info:
            result["drives"].append(info)
    temp = os.environ.get("TEMP", "")
    if temp and Path(temp).exists():
        try:
            tf = list(Path(temp).rglob("*"))
            ts = sum(f.stat().st_size for f in tf if f.is_file())
            tc = sum(1 for f in tf if f.is_file())
            result["temp"] = {"path": temp, "files": tc, "size_bytes": ts}
        except Exception:
            pass
    for folder in [temp, os.path.expanduser("~/Downloads")]:
        if folder and Path(folder).exists():
            try:
                lf = find_largest_files(folder, count=5)
                if lf:
                    result["largest"][folder] = lf
            except Exception:
                pass
    return JSONResponse(result)


@app.get("/api/index-status")
def api_index_status():
    from db.rag_dal import get_all_documents
    from db.connection import init_db
    init_db()
    try:
        docs = get_all_documents()
    except Exception:
        docs = []
    total = len(docs)
    by_drive: dict[str, int] = {}
    for d in docs:
        p = d.get("path", "")
        drive = p[:2] if len(p) > 1 and p[1] == ":" else "other"
        by_drive[drive] = by_drive.get(drive, 0) + 1
    return JSONResponse({"total_docs": total, "by_drive": by_drive})


@app.post("/api/smart-targets")
async def api_smart_targets(request: Request):
    from scan_drives import scan_directory
    from classify_files import classify_file, DEFAULT_RULES
    from generate_plan import generate_moves, DEFAULT_TARGETS, detect_existing_clusters, suggest_targets_from_data

    body = await request.json()
    path = os.path.expanduser(body.get("path", "~/Downloads"))
    files = list(scan_directory(Path(path)))
    for f in files:
        classify_file(f, DEFAULT_RULES)
    suggestions = suggest_targets_from_data(files, DEFAULT_TARGETS)
    return JSONResponse({"suggestions": suggestions})


@app.post("/api/organize")
async def api_organize(request: Request):
    from scan_drives import scan_directory
    from classify_files import classify_file, DEFAULT_RULES
    from generate_plan import generate_moves, DEFAULT_TARGETS, detect_existing_clusters

    body = await request.json()
    path = os.path.expanduser(body.get("path", "~/Downloads"))
    auto = body.get("auto", False)

    files = list(scan_directory(Path(path)))
    for f in files:
        classify_file(f, DEFAULT_RULES)
    counts: dict[str, int] = {}
    for f in files:
        cat = f["category"]
        counts[cat] = counts.get(cat, 0) + 1
    moves = generate_moves(files, DEFAULT_TARGETS)
    clusters = detect_existing_clusters(files, min_cluster=2)
    return JSONResponse({
        "total_files": len(files),
        "categories": counts,
        "moves": moves[:50],
        "total_moves": len(moves),
        "auto": auto,
        "preserved_clusters": clusters,
    })


@app.post("/api/apply")
async def api_apply(request: Request):
    from apply_moves import apply_moves

    body = await request.json()
    moves = body.get("moves", [])
    preserve_folders = body.get("preserve_folders", [])
    preserved = 0
    if preserve_folders:
        filtered = []
        for m in moves:
            src = m.get("source", "")
            skip = False
            for pf in preserve_folders:
                if src.startswith(str(pf)):
                    skip = True
                    preserved += 1
                    break
            if not skip:
                filtered.append(m)
        moves = filtered
    global _last_moves
    results = apply_moves(moves, execute=True, dry_run=False, force=False)
    results["preserved"] = preserved
    if results.get("success", 0) > 0:
        _last_moves = moves
    return JSONResponse(results)


@app.post("/api/query")
async def api_query(request: Request):
    from rag_query import query
    body = await request.json()
    q = body.get("question", "")
    if not q:
        return JSONResponse({"error": "No question provided"})
    scope = body.get("scope", "")
    try:
        result = query(query=q, top_k=5, llm_model="llama3.2", scope=scope)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)})


@app.post("/api/index")
async def api_index(request: Request):
    from index_docs import index_paths
    body = await request.json()
    path = body.get("path", "")
    if not path or not Path(path).exists():
        return JSONResponse({"error": f"Path not found: {path}"})
    try:
        stats = index_paths(paths=[path], recursive=True)
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)})


@app.get("/api/drives")
def api_drives():
    import string
    import ctypes
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(f"{letter}:\\")
        bitmask >>= 1
    return JSONResponse({"drives": drives})


@app.post("/api/browse")
async def api_browse(request: Request):
    body = await request.json()
    path = body.get("path", "")
    if not path or not Path(path).exists():
        return JSONResponse({"error": f"Path not found: {path}"})
    try:
        items = []
        p = Path(path)
        for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                items.append({
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "size": child.stat().st_size if child.is_file() else 0,
                })
            except Exception:
                pass
        return JSONResponse({"path": path, "items": items})
    except Exception as e:
        return JSONResponse({"error": str(e)})


@app.post("/api/undo-organize")
async def api_undo_organize():
    from apply_moves import reverse_moves
    global _last_moves
    if not _last_moves:
        return JSONResponse({"error": "No moves to undo"})
    try:
        result = reverse_moves(_last_moves, execute=True)
        if result.get("success", 0) > 0:
            _last_moves = []
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)})


@app.get("/", response_class=HTMLResponse)
def index():
    html = TEMPLATES / "dashboard.html"
    if html.exists():
        content = html.read_text(encoding="utf-8")
        hostname = socket.gethostname()
        content = content.replace("{{HOSTNAME}}", hostname)
        return HTMLResponse(content, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})
    return HTMLResponse("<h1>Dashboard template not found</h1>", status_code=404)


def run_dashboard(port: int = 8080, open_browser: bool = True):
    if open_browser:
        Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
