"""System resource monitor — CPU, RAM, GPU, processes, Ollama model memory."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import psutil


_gpu_cache: dict = {}
_gpu_cache_time: float = 0
_GPU_CACHE_TTL: float = 10.0  # refresh GPU info every 10 seconds
_cpu_history: list[float] = []


def _parse_ollama_ps() -> list[dict]:
    models: list[dict] = []
    try:
        result = subprocess.run(
            ["ollama", "ps"], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return models
        lines = result.stdout.strip().splitlines()
        if len(lines) < 2:
            return models
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 4:
                name = parts[0]
                size_raw = parts[3] if len(parts) > 3 else "0"
                size_mb = 0
                try:
                    if "GB" in size_raw:
                        size_mb = int(float(size_raw.replace("GB", "").strip()) * 1024)
                    elif "MB" in size_raw:
                        size_mb = int(float(size_raw.replace("MB", "").strip()))
                except ValueError:
                    pass
                models.append({"name": name, "memory_mb": size_mb})
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return models


def _top_processes(count: int = 10) -> list[dict]:
    procs: list[dict] = []
    for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
        try:
            mem = p.info["memory_info"].rss if p.info["memory_info"] else 0
            if mem > 0:
                procs.append({
                    "pid": p.info["pid"],
                    "name": p.info["name"],
                    "memory_bytes": mem,
                    "memory_mb": round(mem / (1024 * 1024), 1),
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(key=lambda x: -x["memory_bytes"])
    return procs[:count]


def get_gpu_info() -> dict:
    global _gpu_cache, _gpu_cache_time
    now = time.time()
    if _gpu_cache and (now - _gpu_cache_time) < _GPU_CACHE_TTL:
        return _gpu_cache

    default = {"name": "N/A", "memory_total_mb": 0, "memory_used_mb": 0,
               "memory_free_mb": 0, "gpu_util": 0, "gpu_temp": 0, "power_watts": 0}
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
            encoding="utf-8", errors="replace",
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = [p.strip() for p in result.stdout.split(",")]
            if len(parts) >= 7:
                _gpu_cache = {
                    "name": parts[0],
                    "memory_total_mb": int(float(parts[1])),
                    "memory_used_mb": int(float(parts[2])),
                    "memory_free_mb": int(float(parts[3])),
                    "gpu_util": int(float(parts[4])),
                    "gpu_temp": int(float(parts[5])),
                    "power_watts": float(parts[6]) if parts[6].replace(".", "").replace("-", "").isdigit() else 0,
                }
                _gpu_cache_time = now
                return _gpu_cache
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return default


def _estimate_cpu_tdp() -> int:
    """Estimate CPU TDP from name. Cached after first call."""
    if hasattr(_estimate_cpu_tdp, '_cached'):
        return _estimate_cpu_tdp._cached
    try:
        result = subprocess.run(
            ["wmic", "cpu", "get", "name"],
            capture_output=True, text=True, timeout=5,
            encoding="utf-8", errors="replace",
        )
        name = result.stdout.strip().split('\n')[-1].strip()
        if name:
            name_l = name.lower()
            if any(x in name_l for x in ['i9', 'ryzen 9', 'threadripper', 'xeon']):
                _estimate_cpu_tdp._cached = 125
            elif any(x in name_l for x in ['i7', 'ryzen 7']):
                _estimate_cpu_tdp._cached = 95
            elif any(x in name_l for x in ['i5', 'ryzen 5']):
                _estimate_cpu_tdp._cached = 65
            elif any(x in name_l for x in ['i3', 'ryzen 3']):
                _estimate_cpu_tdp._cached = 35
            else:
                _estimate_cpu_tdp._cached = 65
        else:
            _estimate_cpu_tdp._cached = 65
    except Exception:
        _estimate_cpu_tdp._cached = 65
    return _estimate_cpu_tdp._cached


def get_resources() -> dict:
    global _cpu_history
    cpu_percent = psutil.cpu_percent(interval=0.3)
    _cpu_history.append(cpu_percent)
    if len(_cpu_history) > 3:
        _cpu_history.pop(0)
    cpu_percent = sum(_cpu_history) / len(_cpu_history)
    cpu_count = psutil.cpu_count()
    cpu_count_logic = psutil.cpu_count(logical=True)
    mem = psutil.virtual_memory()
    gpu = get_gpu_info()
    ollama_models = _parse_ollama_ps()
    processes = _top_processes(10)
    vls_mem = 0
    try:
        vls_mem = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        pass

    ollama_total = sum(m["memory_mb"] for m in ollama_models)
    for p in processes:
        if "ollama" in p["name"].lower():
            ollama_total = max(ollama_total, p["memory_mb"])

    uptime_seconds = int(time.time() - psutil.boot_time())
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    # Power estimation
    cpu_tdp = _estimate_cpu_tdp()
    cpu_power_watts = round(cpu_tdp * (cpu_percent / 100) * 0.7, 1)
    gpu_power_watts = gpu.get("power_watts", 0)
    ram_power_watts = round(0.375 * (mem.total / (1024**3)) * (mem.percent / 100), 1)
    motherboard_watts = 25
    total_power_watts = round(cpu_power_watts + gpu_power_watts + ram_power_watts + motherboard_watts, 1)

    return {
        "cpu": {
            "percent": round(cpu_percent, 1),
            "cores_physical": cpu_count,
            "cores_logical": cpu_count_logic,
            "power_watts": cpu_power_watts,
        },
        "ram": {
            "total_gb": round(mem.total / (1024**3), 1),
            "used_gb": round(mem.used / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "percent": mem.percent,
            "power_watts": ram_power_watts,
        },
        "gpu": gpu,
        "power": {
            "cpu_watts": cpu_power_watts,
            "gpu_watts": gpu_power_watts,
            "ram_watts": ram_power_watts,
            "motherboard_watts": motherboard_watts,
            "total_watts": total_power_watts,
        },
        "ollama": {
            "models": ollama_models,
            "total_memory_mb": ollama_total,
        },
        "processes": processes,
        "vls_memory_mb": round(vls_mem, 1),
        "uptime": {"days": days, "hours": hours, "minutes": minutes},
    }
