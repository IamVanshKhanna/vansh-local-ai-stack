import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_plan import generate_moves, load_targets, parse_target_map

import pytest


# ── parse_target_map ────────────────────────────────────────────────────

def test_parse_target_map_basic():
    result = parse_target_map("documents=~/Docs,media=~/Media")
    assert "documents" in result
    assert "media" in result
    assert Path(result["documents"]) == Path.home() / "Docs"
    assert Path(result["media"]) == Path.home() / "Media"


def test_parse_target_map_single_pair():
    result = parse_target_map("code=~/Projects")
    assert Path(result["code"]) == Path.home() / "Projects"


def test_parse_target_map_skips_invalid():
    result = parse_target_map("documents=~/Docs,bad_entry,media=~/Media")
    assert len(result) == 2
    assert "documents" in result
    assert "media" in result


def test_parse_target_map_whitespace():
    result = parse_target_map(" documents = ~/Docs , media = ~/Media ")
    assert Path(result["documents"]) == Path.home() / "Docs"
    assert Path(result["media"]) == Path.home() / "Media"


# ── load_targets ────────────────────────────────────────────────────────

def test_load_targets_returns_defaults_when_none():
    targets = load_targets(None)
    assert isinstance(targets, dict)
    assert "documents" in targets
    assert "media" in targets
    assert "code" in targets
    assert len(targets) >= 6


# ── generate_moves ─────────────────────────────────────────────────────

def test_generate_moves_creates_moves_for_matching_categories():
    files = [
        {"path": "/tmp/a.pdf", "name": "a.pdf", "category": "documents", "size": 100},
        {"path": "/tmp/b.mp4", "name": "b.mp4", "category": "media", "size": 200},
    ]
    targets = {"documents": "/dest/docs", "media": "/dest/media"}
    moves = generate_moves(files, targets)
    assert len(moves) == 2
    assert Path(moves[0]["destination"]) == Path("/dest/docs/a.pdf")
    assert Path(moves[1]["destination"]) == Path("/dest/media/b.mp4")


def test_generate_moves_skips_unknown_categories():
    files = [
        {"path": "/tmp/a.pdf", "name": "a.pdf", "category": "documents", "size": 100},
        {"path": "/tmp/b.xyz", "name": "b.xyz", "category": "mystery", "size": 50},
    ]
    targets = {"documents": "/dest/docs"}
    moves = generate_moves(files, targets)
    assert len(moves) == 1
    assert moves[0]["category"] == "documents"


def test_generate_moves_returns_empty_for_no_files():
    moves = generate_moves([], {"documents": "/dest"})
    assert moves == []


def test_generate_moves_preserves_size():
    files = [
        {"path": "/tmp/f.txt", "name": "f.txt", "category": "documents", "size": 999},
    ]
    targets = {"documents": "/dest/docs"}
    moves = generate_moves(files, targets)
    assert moves[0]["size"] == 999


def test_generate_moves_defaults_size_to_zero():
    files = [
        {"path": "/tmp/f.txt", "name": "f.txt", "category": "documents"},
    ]
    targets = {"documents": "/dest/docs"}
    moves = generate_moves(files, targets)
    assert moves[0]["size"] == 0
