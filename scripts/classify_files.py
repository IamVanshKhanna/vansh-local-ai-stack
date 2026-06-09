#!/usr/bin/env python3
"""
classify_files.py - Classify files based on rules and optional LLM assistance

Categorizes files from a catalog into predefined categories based on
extension, path patterns, and optional LLM-based classification for
ambiguous files.

Usage:
    python classify_files.py --input catalog.json --output classified.json
    python classify_files.py --input catalog.db --rules custom_rules.yaml
"""

import argparse
import json
import logging
import re
import sqlite3
import sys
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


# Default classification rules
DEFAULT_RULES = {
    "categories": {
        "documents": {
            "extensions": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"],
            "paths": ["documents", "docs"],
        },
        "media": {
            "extensions": [".mp4", ".mkv", ".avi", ".mov", ".mp3", ".wav", ".flac", ".jpg", ".jpeg", ".png", ".gif", ".raw"],
            "paths": ["videos", "movies", "music", "pictures", "photos", "media"],
        },
        "code": {
            "extensions": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".rb", ".php", ".swift", ".kt"],
            "paths": ["projects", "code", "src", "repos", "github"],
        },
        "archives": {
            "extensions": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
            "paths": ["archives", "backups"],
        },
        "executables": {
            "extensions": [".exe", ".msi", ".dmg", ".app", ".deb", ".rpm"],
            "paths": ["installers", "apps"],
        },
        "data": {
            "extensions": [".csv", ".json", ".xml", ".yaml", ".yml", ".db", ".sqlite", ".sql"],
            "paths": ["data", "datasets"],
        },
        "backups": {
            "extensions": [".bak", ".old", ".backup", ".orig"],
            "paths": ["backups", "backup"],
        },
        "downloads": {
            "extensions": [],
            "paths": ["downloads", "download"],
        },
        "system": {
            "extensions": [".dll", ".sys", ".drv"],
            "paths": ["windows", "program files", "system32"],
        },
    },
    "default_category": "uncategorized",
}


def load_catalog(catalog_path: Path) -> list[dict]:
    """Load catalog from JSON or SQLite file."""
    if catalog_path.suffix == ".db":
        conn = sqlite3.connect(catalog_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files")
        columns = [desc[0] for desc in cursor.description]
        files = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return files
    else:
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("files", data)


def classify_by_extension(file_data: dict, rules: dict) -> Optional[str]:
    """Classify file by extension."""
    ext = file_data.get("extension", "").lower()

    for category, rule in rules["categories"].items():
        if ext in rule.get("extensions", []):
            return category

    return None


def classify_by_path(file_data: dict, rules: dict) -> Optional[str]:
    """Classify file by path patterns."""
    path = file_data.get("path", "").lower()

    for category, rule in rules["categories"].items():
        for pattern in rule.get("paths", []):
            if pattern.lower() in path:
                return category

    return None


def classify_with_llm(file_data: dict, model: str = "llama3.2") -> str:
    """Classify ambiguous file using LLM."""
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    filename = file_data.get("name", "")
    extension = file_data.get("extension", "")
    parent = file_data.get("parent", "")

    prompt = f"""Classify this file into exactly one category from this list:
categories: documents, media, code, archives, executables, data, backups, downloads, system, other

Filename: {filename}
Extension: {extension or "none"}
Directory: {parent}

Category:"""

    try:
        response = requests.post(
            f"{ollama_host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 10}
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json().get("response", "").strip().lower()

        # Valid categories
        valid = {"documents", "media", "code", "archives", "executables", "data", "backups", "downloads", "system", "other"}

        if result in valid:
            return result

        # Try to extract category
        for cat in valid:
            if cat in result:
                return cat

        return "uncategorized"

    except Exception as e:
        logger.warning(f"LLM classification failed: {e}")
        return "uncategorized"


def classify_file(file_data: dict, rules: dict, use_llm: bool = False) -> dict:
    """Classify a single file."""
    # Try extension-based first
    category = classify_by_extension(file_data, rules)

    # Try path-based
    if not category:
        category = classify_by_path(file_data, rules)

    # Use LLM for ambiguous files
    if not category and use_llm:
        category = classify_with_llm(file_data)

    # Default
    if not category:
        category = rules.get("default_category", "uncategorized")

    file_data["category"] = category
    return file_data


def main():
    parser = argparse.ArgumentParser(
        description="Classify files from catalog"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input catalog file (.json or .db)"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output classification file (.json)"
    )
    parser.add_argument(
        "--rules", "-r",
        help="Custom rules YAML file"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM for ambiguous files (requires Ollama)"
    )
    parser.add_argument(
        "--model",
        default="llama3.2",
        help="LLM model for classification (default: llama3.2)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load rules (use default for now)
    rules = DEFAULT_RULES

    # Load catalog
    catalog_path = Path(args.input)
    if not catalog_path.exists():
        logger.error(f"Catalog not found: {catalog_path}")
        sys.exit(1)

    logger.info(f"Loading catalog: {catalog_path}")
    files = load_catalog(catalog_path)
    logger.info(f"Loaded {len(files)} files")

    # Classify files
    classified = []
    category_counts = {}

    for file_data in files:
        result = classify_file(file_data, rules, args.use_llm)
        classified.append(result)

        cat = result["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "version": "1.0",
        "classified_date": datetime.now().isoformat(),
        "total_files": len(classified),
        "category_counts": category_counts,
        "files": classified,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"Saved classification to {output_path}")

    # Print summary
    print(f"\nClassification Summary:")
    print(f"  Total files: {len(classified)}")
    print(f"\nCategories:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        pct = (count / len(classified)) * 100
        print(f"  {cat}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
