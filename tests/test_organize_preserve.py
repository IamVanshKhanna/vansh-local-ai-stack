import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_plan import detect_existing_clusters


# ── detect_existing_clusters ─────────────────────────────────────────────

def test_clusters_empty_folder():
    files = []
    clusters = detect_existing_clusters(files, min_cluster=2)
    assert clusters == []


def test_clusters_single_file():
    files = [
        {"path": str(Path("/tmp/sub/file.txt")), "name": "file.txt"},
    ]
    clusters = detect_existing_clusters(files, min_cluster=2)
    assert clusters == []


def test_clusters_two_files_same_folder():
    files = [
        {"path": str(Path("/tmp/sub/a.txt")), "name": "a.txt"},
        {"path": str(Path("/tmp/sub/b.txt")), "name": "b.txt"},
    ]
    clusters = detect_existing_clusters(files, min_cluster=2)
    assert len(clusters) == 1
    assert clusters[0]["folder"] == str(Path("/tmp/sub"))
    assert clusters[0]["files"] == 2


def test_clusters_three_subfolders():
    files = [
        {"path": str(Path("/tmp/sub1/a.txt")), "name": "a.txt"},
        {"path": str(Path("/tmp/sub1/b.txt")), "name": "b.txt"},
        {"path": str(Path("/tmp/sub2/c.txt")), "name": "c.txt"},
        {"path": str(Path("/tmp/sub2/d.txt")), "name": "d.txt"},
        {"path": str(Path("/tmp/sub2/e.txt")), "name": "e.txt"},
    ]
    clusters = detect_existing_clusters(files, min_cluster=2)
    assert len(clusters) == 2
    names = {c["folder"] for c in clusters}
    assert str(Path("/tmp/sub1")) in names
    assert str(Path("/tmp/sub2")) in names


def test_clusters_mixed_loose_and_clustered():
    files = [
        {"path": str(Path("/tmp/loose.txt")), "name": "loose.txt"},
        {"path": str(Path("/tmp/sub1/a.txt")), "name": "a.txt"},
        {"path": str(Path("/tmp/sub1/b.txt")), "name": "b.txt"},
        {"path": str(Path("/tmp/sub1/c.txt")), "name": "c.txt"},
    ]
    clusters = detect_existing_clusters(files, min_cluster=2)
    assert len(clusters) == 1
    assert clusters[0]["folder"] == str(Path("/tmp/sub1"))
    assert clusters[0]["files"] == 3


def test_clusters_custom_min_cluster():
    files = [
        {"path": str(Path("/tmp/sub/a.txt")), "name": "a.txt"},
        {"path": str(Path("/tmp/sub/b.txt")), "name": "b.txt"},
        {"path": str(Path("/tmp/sub/c.txt")), "name": "c.txt"},
    ]
    clusters = detect_existing_clusters(files, min_cluster=4)
    assert clusters == []
