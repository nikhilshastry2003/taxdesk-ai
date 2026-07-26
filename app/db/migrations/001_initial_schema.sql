 -- Migration 001: initial schema.
-- Approved design: docs/design/001-data-model.md (2026-07-12).
-- No PRAGMA here: foreign_keys is per-connection in SQLite, so the
-- runner's connect() sets it for every connection, not just this script.

-- The parties dad works for. folder_path links each client to its folder on disk.
CREATE TABLE clients (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    folder_path TEXT,
    phone       TEXT,
    email       TEXT,
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Which of the 4 services apply to each client. Own table (not columns on clients)
-- so a future 5th service is a new row, not a schema change.
CREATE TABLE client_services (
    id           INTEGER PRIMARY KEY,
    client_id    INTEGER NOT NULL REFERENCES clients(id),
    service_type TEXT NOT NULL CHECK (service_type IN ('GSTR_3B','GSTR_1','EPF','ESI')),
    active       INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    notes        TEXT,
    UNIQUE (client_id, service_type)
);

-- One row per tracked month. Tasks point here instead of repeating month/year strings.
CREATE TABLE compliance_periods (
    id             INTEGER PRIMARY KEY,
    month          INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    year           INTEGER NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    financial_year TEXT NOT NULL,              -- e.g. '2026-27'
    status         TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed')),
    UNIQUE (month, year)
);

-- The heart of the model: one row = one client x one service x one period.
-- Every page (Dashboard, Priority, EPF, ESI) is a query over this table.
CREATE TABLE compliance_tasks (
    id              INTEGER PRIMARY KEY,
    client_id       INTEGER NOT NULL REFERENCES clients(id),
    period_id       INTEGER NOT NULL REFERENCES compliance_periods(id),
    service_type    TEXT NOT NULL CHECK (service_type IN ('GSTR_3B','GSTR_1','EPF','ESI')),
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','done','not_applicable')),
    due_date        TEXT,                      -- ISO 'YYYY-MM-DD'
    proof_status    TEXT NOT NULL DEFAULT 'missing' CHECK (proof_status IN ('missing','detected','linked','not_required')),
    proof_file_path TEXT,
    completed_at    TEXT,
    completed_source TEXT CHECK (completed_source IN ('manual','scan_confirmed')),
    notes           TEXT,
    UNIQUE (client_id, period_id, service_type)   -- duplicate generation is impossible
);

-- Saved file links for the Documents page search, independent of tasks.
CREATE TABLE documents (
    id             INTEGER PRIMARY KEY,
    client_id      INTEGER NOT NULL REFERENCES clients(id),
    period_id      INTEGER REFERENCES compliance_periods(id),   -- nullable: not every file belongs to a month
    document_type  TEXT NOT NULL CHECK (document_type IN ('gstr_3b','gstr_1','epf_ecr','esi_challan','itr_ack','other')),
    file_path      TEXT NOT NULL,
    filename       TEXT NOT NULL,
    document_date  TEXT,
    year           INTEGER,
    financial_year TEXT,
    notes          TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- App-level key-value facts. First row: ('root_folder', dad's client folder root).
CREATE TABLE settings (
    key   TEXT PRIMARY KEY,     -- e.g. 'root_folder'
    value TEXT NOT NULL
);
