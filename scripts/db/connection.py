"""Database connection helper for SQLite catalog."""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).parent / "catalog.db"

_db_path: Path = DEFAULT_DB_PATH


def set_db_path(path: Path) -> None:
    """Set the database file path used by all DAL functions."""
    global _db_path
    _db_path = path
    logger.info("Database path set to %s", path)


def get_db_path() -> Path:
    """Return the resolved database file path."""
    return _db_path


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open a SQLite connection with row factory and foreign keys enabled."""
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    logger.debug("Opened connection to %s", path)
    return conn


def init_db(conn: Optional[sqlite3.Connection] = None, db_path: Optional[Path] = None) -> None:
    """Run the bundled schema.sql to create tables and indexes."""
    schema_path = Path(__file__).parent / "schema.sql"
    own_conn = False
    if conn is None:
        conn = get_connection(db_path)
        own_conn = True
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    if own_conn:
        conn.close()
    logger.info("Database initialized from %s", schema_path)
