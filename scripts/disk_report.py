#!/usr/bin/env python3
"""
disk_report.py - Generate disk space usage reports

Analyzes disk space usage and generates reports in various formats.

Usage:
    python disk_report.py --drives "C,D,E" --output report.json
    python disk_report.py --drives "C" --format markdown --output report.md
    python disk_report.py --threshold 90 --alert  # Alert if any drive > 90%
"""

import argparse
import json
import logging
import platform
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


def get_drive_info(path: str) -> dict:
    """Get disk usage information for a drive/path."""
    try:
        usage = shutil.disk_usage(path)

        total_gb = usage.total / (1024**3)
        used_gb = usage.used / (1024**3)
        free_gb = usage.free / (1024**3)
        used_percent = (usage.used / usage.total) * 100

        return {
            "path": path,
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "used_percent": round(used_percent, 2),
            "status": "ok" if used_percent < 90 else "warning" if used_percent < 95 else "critical",
        }

    except Exception as e:
        return {
            "path": path,
            "error": str(e),
            "status": "error",
        }


def get_all_drives() -> list[str]:
    """Get list of all available drives."""
    system = platform.system()

    if system == "Windows":
        import string
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if Path(drive).exists():
                drives.append(drive)
        return drives

    else:  # Linux/macOS
        return ["/"]


def find_largest_files(directory: str, count: int = 10) -> list[dict]:
    """Find the largest files in a directory."""
    logger.info(f"Finding largest files in {directory}")

    files = []
    directory_path = Path(directory)

    try:
        for path in directory_path.rglob("*"):
            if path.is_file():
                try:
                    size = path.stat().st_size
                    files.append({
                        "path": str(path),
                        "size": size,
                        "size_human": format_size(size),
                    })
                except (PermissionError, OSError):
                    pass
    except Exception as e:
        logger.warning(f"Error scanning {directory}: {e}")

    # Sort by size and return top
    files.sort(key=lambda x: x["size"], reverse=True)
    return files[:count]


def format_size(size: int) -> str:
    """Format size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def generate_report(
    drives: list[str],
    include_large_files: bool = False,
    large_file_count: int = 10
) -> dict:
    """Generate disk usage report."""
    report = {
        "generated": datetime.now().isoformat(),
        "drives": [],
        "alerts": [],
    }

    for drive in drives:
        info = get_drive_info(drive)
        report["drives"].append(info)

        # Check thresholds
        if info.get("status") == "critical":
            report["alerts"].append({
                "level": "critical",
                "message": f"Drive {drive} is at {info['used_percent']}% capacity",
                "drive": drive,
            })
        elif info.get("status") == "warning":
            report["alerts"].append({
                "level": "warning",
                "message": f"Drive {drive} is at {info['used_percent']}% capacity",
                "drive": drive,
            })

        # Find large files if requested
        if include_large_files and "error" not in info:
            large_files = find_largest_files(drive, large_file_count)
            info["largest_files"] = large_files

    return report


def format_markdown(report: dict) -> str:
    """Format report as markdown."""
    lines = [
        "# Disk Space Report",
        f"\nGenerated: {report['generated']}",
        "",
        "## Drive Summary",
        "",
        "| Drive | Total | Used | Free | Usage | Status |",
        "|-------|-------|------|------|-------|--------|",
    ]

    for drive in report["drives"]:
        if "error" in drive:
            lines.append(f"| {drive['path']} | Error: {drive['error']} | | | | |")
        else:
            lines.append(
                f"| {drive['path']} | {drive['total_gb']} GB | "
                f"{drive['used_gb']} GB | {drive['free_gb']} GB | "
                f"{drive['used_percent']}% | {drive['status']} |"
            )

    if report["alerts"]:
        lines.extend([
            "",
            "## Alerts",
            "",
        ])
        for alert in report["alerts"]:
            lines.append(f"- **{alert['level'].upper()}**: {alert['message']}")

    return "\n".join(lines)


def send_alert(report: dict, config: dict):
    """Send alert notification (placeholder for actual implementation)."""
    alerts = report.get("alerts", [])
    if not alerts:
        return

    # Placeholder: Log alerts
    for alert in alerts:
        logger.warning(f"ALERT [{alert['level']}]: {alert['message']}")

    # TODO: Implement actual alerting (email, webhook, etc.)
    # Example:
    # if config.get("email"):
    #     send_email(config["email"], alerts)
    # if config.get("webhook"):
    #     requests.post(config["webhook"], json=alerts)


def main():
    parser = argparse.ArgumentParser(
        description="Generate disk space usage report"
    )
    parser.add_argument(
        "--drives", "-d",
        help="Comma-separated list of drives to analyze (default: all)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown", "text"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--include-large-files",
        action="store_true",
        help="Include list of largest files"
    )
    parser.add_argument(
        "--large-file-count",
        type=int,
        default=10,
        help="Number of large files to show (default: 10)"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=90,
        help="Alert threshold percentage (default: 90)"
    )
    parser.add_argument(
        "--alert",
        action="store_true",
        help="Send alert if threshold exceeded"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine drives to analyze
    if args.drives:
        drives = [d.strip() for d in args.drives.split(",")]
    else:
        drives = get_all_drives()

    logger.info(f"Analyzing drives: {drives}")

    # Generate report
    report = generate_report(
        drives,
        include_large_files=args.include_large_files,
        large_file_count=args.large_file_count,
    )

    # Output
    if args.format == "markdown":
        output = format_markdown(report)
    else:
        output = json.dumps(report, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)

        logger.info(f"Report saved to {output_path}")
    else:
        print(output)

    # Send alerts if requested
    if args.alert:
        send_alert(report, {})

    # Exit with error if any critical alerts
    critical_alerts = [a for a in report.get("alerts", []) if a["level"] == "critical"]
    if critical_alerts:
        sys.exit(1)


if __name__ == "__main__":
    main()
