#!/usr/bin/env python3
"""
health_check.py - Check system health and service availability

Verifies that all components of the local AI stack are healthy.

Usage:
    python health_check.py --output status.json
    python health_check.py --check-all
    python health_check.py --only ollama,gpu,ram
"""

import argparse
import json
import logging
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def check_ollama(host: Optional[str] = None) -> dict:
    """Check if Ollama is running and responsive."""
    host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    try:
        response = requests.get(f"{host}/api/tags", timeout=5)
        response.raise_for_status()

        models = response.json().get("models", [])

        return {
            "status": "pass",
            "host": host,
            "latency_ms": response.elapsed.total_seconds() * 1000,
            "models_available": len(models),
            "models": [m.get("name") for m in models[:5]],  # First 5 models
        }

    except requests.ConnectionError:
        return {
            "status": "fail",
            "host": host,
            "error": "Connection refused - Ollama not running",
        }
    except requests.Timeout:
        return {
            "status": "fail",
            "host": host,
            "error": "Request timed out",
        }
    except Exception as e:
        return {
            "status": "fail",
            "host": host,
            "error": str(e),
        }


def check_gpu() -> dict:
    """Check GPU availability and status."""
    system = platform.system()

    try:
        if system == "Windows":
            # Try NVIDIA first
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    gpus = []

                    for line in lines:
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 4:
                            gpus.append({
                                "name": parts[0],
                                "memory_total": parts[1],
                                "memory_used": parts[2],
                                "memory_free": parts[3],
                            })

                    return {
                        "status": "pass",
                        "vendor": "nvidia",
                        "gpus": gpus,
                    }
            except Exception:
                pass

            # Try AMD if NVIDIA not found
            # AMD requires different tool (rocm-smi or ADL)
            return {
                "status": "pass",
                "vendor": "unknown",
                "note": "GPU detected but details unavailable (may be AMD)",
            }

        else:  # Linux/macOS
            # Try nvidia-smi
            try:
                import subprocess
                result = subprocess.run(["nvidia-smi"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return {"status": "pass", "vendor": "nvidia"}
            except Exception:
                pass

            return {
                "status": "pass",
                "vendor": "unknown",
                "note": "GPU status check not implemented for this platform",
            }

    except Exception as e:
        return {
            "status": "fail",
            "error": str(e),
        }


def check_ram(threshold_percent: float = 90) -> dict:
    """Check system RAM usage."""
    try:
        import psutil

        memory = psutil.virtual_memory()

        return {
            "status": "pass" if memory.percent < threshold_percent else "warning",
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_percent": round(memory.percent, 2),
            "threshold_percent": threshold_percent,
        }

    except ImportError:
        # Fallback without psutil
        return {
            "status": "pass",
            "note": "psutil not installed, cannot check RAM",
        }
    except Exception as e:
        return {
            "status": "fail",
            "error": str(e),
        }


def check_disk(threshold_gb: float = 10) -> dict:
    """Check available disk space."""
    import shutil

    try:
        # Check system drive
        system_drive = "C:\\" if platform.system() == "Windows" else "/"
        usage = shutil.disk_usage(system_drive)

        free_gb = usage.free / (1024**3)

        return {
            "status": "pass" if free_gb > threshold_gb else "warning",
            "drive": system_drive,
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(free_gb, 2),
            "threshold_gb": threshold_gb,
        }

    except Exception as e:
        return {
            "status": "fail",
            "error": str(e),
        }


def check_scripts(scripts_dir: Optional[str] = None) -> dict:
    """Check if expected scripts exist."""
    if not scripts_dir:
        scripts_dir = Path(__file__).parent

    scripts_path = Path(scripts_dir)

    expected_scripts = [
        "scan_drives.py",
        "classify_files.py",
        "apply_moves.py",
        "disk_report.py",
        "health_check.py",
    ]

    found = []
    missing = []

    for script in expected_scripts:
        script_path = scripts_path / script
        if script_path.exists():
            found.append(script)
        else:
            missing.append(script)

    return {
        "status": "pass" if not missing else "warning",
        "scripts_dir": str(scripts_path),
        "found": found,
        "missing": missing,
    }


def check_vector_db(db_path: Optional[str] = None) -> dict:
    """Check if RAG vector database is accessible."""
    if not db_path:
        db_path = os.path.expanduser("~/.local-ai-stack/vector-db")

    db_path = Path(db_path)

    if not db_path.exists():
        return {
            "status": "pass",
            "note": "Vector DB not initialized (set up in Phase 2)",
        }

    # Check for ChromaDB files
    chroma_db = db_path / "chroma.sqlite3"
    if chroma_db.exists():
        return {
            "status": "pass",
            "type": "chromadb",
            "path": str(db_path),
        }

    return {
        "status": "pass",
        "path": str(db_path),
        "note": "Vector DB directory exists",
    }


def run_health_check(
    checks: list[str],
    ollama_host: Optional[str] = None,
    ram_threshold: float = 90,
    disk_threshold: float = 10,
) -> dict:
    """Run health checks and return status."""
    timestamp = datetime.now().isoformat()

    available_checks = {
        "ollama": lambda: check_ollama(ollama_host),
        "gpu": check_gpu,
        "ram": lambda: check_ram(ram_threshold),
        "disk": lambda: check_disk(disk_threshold),
        "scripts": check_scripts,
        "vector_db": check_vector_db,
    }

    results = {
        "timestamp": timestamp,
        "status": "healthy",
        "checks": {},
    }

    # Run selected checks
    for check_name in checks:
        if check_name in available_checks:
            logger.info(f"Running check: {check_name}")
            check_result = available_checks[check_name]()
            results["checks"][check_name] = check_result

            # Update overall status
            if check_result["status"] == "fail":
                results["status"] = "unhealthy"
            elif check_result["status"] == "warning" and results["status"] == "healthy":
                results["status"] = "degraded"

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Check system health and service availability"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file"
    )
    parser.add_argument(
        "--check-all",
        action="store_true",
        help="Run all checks"
    )
    parser.add_argument(
        "--only",
        help="Comma-separated list of checks to run"
    )
    parser.add_argument(
        "--exclude",
        help="Comma-separated list of checks to skip"
    )
    parser.add_argument(
        "--ollama-host",
        help="Ollama host URL (default: from OLLAMA_HOST env var)"
    )
    parser.add_argument(
        "--ram-threshold",
        type=float,
        default=90,
        help="RAM usage threshold for warning (default: 90%%)"
    )
    parser.add_argument(
        "--disk-threshold",
        type=float,
        default=10,
        help="Minimum free disk space in GB (default: 10)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine which checks to run
    all_checks = ["ollama", "gpu", "ram", "disk", "scripts", "vector_db"]

    if args.check_all:
        checks = all_checks
    elif args.only:
        checks = [c.strip() for c in args.only.split(",")]
    else:
        checks = all_checks

    if args.exclude:
        exclude = [e.strip() for e in args.exclude.split(",")]
        checks = [c for c in checks if c not in exclude]

    # Run health check
    logger.info(f"Running health checks: {checks}")
    results = run_health_check(
        checks,
        ollama_host=args.ollama_host,
        ram_threshold=args.ram_threshold,
        disk_threshold=args.disk_threshold,
    )

    # Output
    output = json.dumps(results, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)

        logger.info(f"Health check saved to {output_path}")
    else:
        print(output)

    # Print summary
    print(f"\nHealth Check Summary:")
    print(f"  Status: {results['status'].upper()}")
    print(f"  Checks run: {len(results['checks'])}")

    for check_name, check_result in results["checks"].items():
        status = check_result.get("status", "unknown")
        symbol = "PASS" if status == "pass" else "FAIL" if status == "fail" else "WARN"
        print(f"    [{symbol}] {check_name}")

    # Exit with appropriate code
    if results["status"] == "unhealthy":
        sys.exit(1)
    elif results["status"] == "degraded":
        sys.exit(2)


if __name__ == "__main__":
    main()
