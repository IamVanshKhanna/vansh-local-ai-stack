-- vansh-local-ai-stack database schema
-- SQLite catalog for scans, files, classifications, and moves

CREATE TABLE IF NOT EXISTS scans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date   TEXT NOT NULL DEFAULT (datetime('now')),
    root_paths  TEXT NOT NULL,
    file_count  INTEGER NOT NULL DEFAULT 0,
    total_size  INTEGER NOT NULL DEFAULT 0,
    skip_hidden INTEGER NOT NULL DEFAULT 1,
    status      TEXT NOT NULL DEFAULT 'in_progress',
    note        TEXT
);

CREATE TABLE IF NOT EXISTS files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id     INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    path        TEXT NOT NULL,
    name        TEXT NOT NULL,
    extension   TEXT,
    size        INTEGER NOT NULL DEFAULT 0,
    size_human  TEXT,
    modified    TEXT,
    created     TEXT,
    parent      TEXT,
    UNIQUE(scan_id, path)
);

CREATE TABLE IF NOT EXISTS classifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id     INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    category    TEXT NOT NULL,
    method      TEXT NOT NULL DEFAULT 'rule',
    confidence  REAL,
    classified_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(scan_id, file_id)
);

CREATE TABLE IF NOT EXISTS move_plans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id     INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    target_structure TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'draft',
    note        TEXT
);

CREATE TABLE IF NOT EXISTS move_operations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id     INTEGER NOT NULL REFERENCES move_plans(id) ON DELETE CASCADE,
    file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    source      TEXT NOT NULL,
    destination TEXT NOT NULL,
    operation   TEXT NOT NULL DEFAULT 'move',
    status      TEXT NOT NULL DEFAULT 'pending',
    executed_at TEXT,
    error       TEXT
);

CREATE INDEX IF NOT EXISTS idx_files_scan_id ON files(scan_id);
CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension);
CREATE INDEX IF NOT EXISTS idx_files_category ON classifications(category);
CREATE INDEX IF NOT EXISTS idx_moves_plan_id ON move_operations(plan_id);
