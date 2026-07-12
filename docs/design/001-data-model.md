# Design Note 001 - Client And Compliance Task Data Model

Status: Approved by Nikhil (Tech Lead), 2026-07-12. Schema is cleared for implementation as migration 001.

Date: 2026-07-12

Roadmap milestone: v0.2 - Domain and database design.

---

## Problem

Dad tracks pending GSTR-3B, GSTR-1, EPF, and ESI work per client in an Excel tick-mark sheet. TaxDesk needs a database model that can answer, for any month:

```text
Which clients have pending work, for which service, and where is the proof?
```

Every MVP page (Dashboard, Priority, Client, EPF, ESI, Documents) is a different view of this same data.

## Why It Matters

This is the foundation everything else builds on. The hardest requirement - "Priority must exactly mirror Dashboard" - is satisfied structurally: both pages run queries over one `compliance_tasks` table, so they cannot disagree. Get this model right and the UI becomes simple; get it wrong and every page needs correction logic.

## User Workflow Served

1. Dad points TaxDesk at his root client folder once (e.g. `D:\Clients`). TaxDesk discovers the per-client subfolders, fills each client's folder path automatically, and dad confirms the list.
2. Dad marks which services apply to each client (e.g. ABC Traders: GSTR-3B + EPF). TaxDesk may pre-suggest services from what it sees inside the folder.
3. Each month, TaxDesk generates one pending task per client per active service.
4. Dashboard counts pending tasks; Priority lists them; dad marks tasks done.
5. Documents link saved files (challans, acknowledgements) to clients and periods.

---

## Concepts Used (read before the schema)

**Entity.** A thing the business tracks: a client, a period, a task. Each entity becomes a table; each row is one instance.

**Primary key (PK).** A column that uniquely identifies a row. We use `id INTEGER PRIMARY KEY` - in SQLite this is the built-in rowid, auto-assigned. Names change, spellings vary; the id never does, so all references use it.

**Foreign key (FK).** A column holding another table's PK, creating a relationship. `compliance_tasks.client_id` points at `clients.id`. The database then refuses tasks for clients that don't exist. SQLite gotcha: FK enforcement is OFF by default - every connection must run `PRAGMA foreign_keys = ON`. Forgetting this is the most common SQLite mistake; our db module will do it in one place.

**Why `client_services` is a separate table (normalization).** The alternative is four boolean columns on `clients` (`has_gstr3b`, `has_gstr1`, ...). That works until the fifth service appears - then every table change is a schema migration. As a separate table, "ABC Traders now files PT" is just a new row. Rule of thumb: when an attribute repeats per item ("client HAS MANY services"), it wants its own table.

**UNIQUE constraint as a business rule.** `UNIQUE (client_id, period_id, service_type)` on tasks means the database itself makes duplicate task generation impossible - even if the generation code runs twice. Rules enforced by the schema cannot be broken by buggy code; rules enforced only in code can.

**CHECK constraint as a lightweight enum.** `CHECK (status IN ('pending','done','not_applicable'))` rejects typos like `'Done'` at write time. The alternative (a lookup table per enum) adds joins without adding value at this scale.

**Dates as TEXT.** SQLite has no DATE type. Convention: store ISO strings (`'2026-07-20'`), which sort and compare correctly as text.

**Derived data is computed, never stored.** There is no `pending_count` column anywhere. Counts are `SELECT COUNT(*)` at read time. A stored count can drift from the truth; a computed one cannot. This single rule is what guarantees Dashboard = Priority.

---

## Proposed Schema (draft - review before it becomes migration 001)

```sql
PRAGMA foreign_keys = ON;   -- run on every connection, not just here

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

CREATE TABLE client_services (
    id           INTEGER PRIMARY KEY,
    client_id    INTEGER NOT NULL REFERENCES clients(id),
    service_type TEXT NOT NULL CHECK (service_type IN ('GSTR_3B','GSTR_1','EPF','ESI')),
    active       INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    notes        TEXT,
    UNIQUE (client_id, service_type)
);

CREATE TABLE compliance_periods (
    id             INTEGER PRIMARY KEY,
    month          INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    year           INTEGER NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    financial_year TEXT NOT NULL,              -- e.g. '2026-27'
    status         TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed')),
    UNIQUE (month, year)
);

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

CREATE TABLE settings (
    key   TEXT PRIMARY KEY,     -- e.g. 'root_folder'
    value TEXT NOT NULL
);
```

## Deviations From The Architecture Draft

Deliberate changes against `docs/architecture.md`:

- **`task_label` column dropped.** The draft had both `service_type` ('GSTR_3B') and `task_label` ('GSTR-3B'). The label is derivable from the type, so storing both invites drift (a row where type says GSTR_3B but label says GSTR-1). Display labels become one small mapping in Python code. Same reasoning as the no-stored-counts rule: never store what you can derive.

- **Added since the draft:** the `'detected'` proof status, the `completed_source` column, and the `settings` table - all from the proof-detection and folder-mapping decisions below (2026-07-12).

If approved, `docs/architecture.md` gets updated to match in the same PR that implements this.

## Folder Mapping And Onboarding (Decided 2026-07-12)

Dad already keeps one folder per client under a single root. TaxDesk uses that instead of asking him to type paths.

Where paths live - two places, two different jobs:

- `settings.root_folder` - the one root dad picks at first launch (e.g. `D:\Clients`). A key-value settings table holds it; one row, no schema change when new settings appear later.
- `clients.folder_path` - each client's own folder. Filled automatically at onboarding: TaxDesk lists the root's subfolders, matches or creates clients from folder names, dad confirms the list once. Editable afterwards.
- `compliance_tasks.proof_file_path` - the exact file proving one task. Filled by the scanner as a detected suggestion, or by dad manually.

The flow, end to end:

```text
dad picks root folder  ->  subfolders discovered  ->  clients.folder_path filled   (one time)
scanner walks each client's folder_path
  -> filename patterns say "this is GSTR-3B, July 2026"
  -> finds the matching compliance_tasks row (client + service + period)
  -> sets proof_status = 'detected', proof_file_path = that file
dad clicks confirm -> status = 'done', proof_status = 'linked'
```

Generalization rule (why this fits other offices later without schema changes): the schema holds what is universal to every tax practice - clients, services, periods, tasks, proofs. What varies per office (folder layout, naming habits) lives as DATA: the root path is a settings row, and matching rules become rows in a patterns table designed in Design Note 002. Another office = different rows, same schema, same code.

## Proof Auto-Detection (Decided Into MVP Scope, 2026-07-12)

Product rule: dad should not have to tick tasks that his own saved files already prove. When he drops a challan or acknowledgement into the client folder, TaxDesk should notice.

Decisions made (Nikhil, 2026-07-12):

- In MVP scope, built around the Documents milestone (v0.6).
- Confirm-first policy: a detected file sets `proof_status = 'detected'`; dad confirms with one click, which sets `status = 'done'`, `proof_status = 'linked'`, `completed_source = 'scan_confirmed'`. Full-auto becomes a setting only after matching proves trustworthy in real use ('auto_scan' value added by a future migration then, not before).
- Every automatic change shows its reason (which file, found when) and is undoable in one click. A wrong silent auto-done is the one bug that would destroy dad's trust in the dashboard.
- Deterministic only: folder walk plus filename/path matching rules. No AI, no OCR, no background daemon - scan runs at app open and via a "Scan now" button.

Status flow for proof_status:

```text
missing -> detected (scanner found a candidate)
detected -> linked  (dad confirms; task becomes done, source recorded)
missing -> linked   (dad links manually - always possible, scanner or not)
any     -> not_required (manual mark)
```

How this note is affected: only the schema hooks (`'detected'` in proof_status, `completed_source`, and the `settings` table from the folder-mapping section). The scanner itself - matching rules, scan bookkeeping, briefing panel - is Design Note 002, which CANNOT be written until we have the real folder listings (Open Question 4).

## Key Queries This Model Must Serve (continued)

Confirmation inbox ("since last open, these look done - confirm?"):

```sql
SELECT c.name, t.service_type, t.proof_file_path
FROM compliance_tasks t
JOIN clients c ON c.id = t.client_id
WHERE t.period_id = ? AND t.proof_status = 'detected';
```

## Key Queries This Model Must Serve

Dashboard pending counts for a period:

```sql
SELECT service_type, COUNT(*) AS pending
FROM compliance_tasks
WHERE period_id = ? AND status = 'pending'
GROUP BY service_type;
```

Priority / EPF / ESI page (same data, filtered and joined to names):

```sql
SELECT c.name, t.service_type, t.due_date, t.proof_status
FROM compliance_tasks t
JOIN clients c ON c.id = t.client_id
WHERE t.period_id = ? AND t.status = 'pending' AND t.service_type = ?
ORDER BY t.due_date, c.name;
```

Monthly task generation (idempotent thanks to the UNIQUE constraint):

```sql
INSERT OR IGNORE INTO compliance_tasks (client_id, period_id, service_type, due_date)
SELECT cs.client_id, ?, cs.service_type, ?
FROM client_services cs
WHERE cs.active = 1;
```

## Edge Cases And The Rules That Handle Them

- **Generation runs twice for the same month** -> `INSERT OR IGNORE` + UNIQUE: second run inserts nothing. This is the exact bug dad's Excel can't protect against.
- **Client with no active services** -> generation selects nothing; client never appears on Dashboard.
- **Service deactivated mid-month** -> already-generated tasks REMAIN (they are history/facts); future generations skip the service. Deactivation is not deletion.
- **Deleting a client that has tasks** -> FK blocks it. MVP has no client deletion; later we add an `archived` flag instead (same pattern as `active` on services).
- **Closed period** -> application rule (not schema): task generation and status changes are refused when `compliance_periods.status = 'closed'`.
- **Proof file moved/renamed on disk** -> `proof_file_path` may dangle; MVP stores and opens paths, it does not verify them. Documents page behavior, not a schema concern.
- **A subfolder under the root is not a client** (e.g. `Backup`, `Old`) -> onboarding shows the discovered list and dad unticks non-clients before anything is created.
- **Client folder renamed or moved** -> `folder_path` dangles; the scan reports "folder not found" for that client instead of silently showing zero files.
- **Scanner matches the wrong file (e.g. a draft challan)** -> confirm-first policy: nothing is marked done without dad's click, so a false detection costs one glance, not a missed filing.
- **File deleted after detection but before confirmation** -> confirmation re-checks the file exists; if gone, the task drops back to `proof_status = 'missing'`.

## Open Questions (need dad / Nikhil before implementation)

1. **Due-date rules per service.** GSTR-3B, GSTR-1, EPF, ESI each have standard monthly due dates dad knows cold. Confirm the day-of-month rule for each so generation can fill `due_date` automatically. (Not hardcoding my assumptions - dad is the source.)
2. **Financial year format.** Proposed `'2026-27'`. Match whatever dad writes on folders.
3. **Should `not_applicable` exist at generation time,** or only as a manual mark after? Proposed: only manual.
4. **Real filenames (blocks Design Note 002 - the scanner).** No workflow interview needed - dad already keeps one folder per client under one root. What we still need: directory listings of 2-3 real client folders (a `dir /s` dump, ~10 minutes), because matching rules written before seeing real filenames are guesses. Likely luck: portal-downloaded files usually carry structured names (period, return type) - if dad keeps them unrenamed, matching gets very reliable. Verify from the listings.

## Expected Files When Implemented (after review)

```text
app/db/migrations/001_initial_schema.sql   -- the DDL above
app/db/migrate.py                          -- tiny runner: applies pending .sql files, records them in schema_migrations
app/db/seed.py                             -- 5-10 sample clients, services, one period, generated tasks
docs/architecture.md                       -- task_label removal reflected
```

Zero new dependencies: `sqlite3` is in Python's standard library. `fastapi`/`uvicorn`/`jinja2` enter later, when the first page is built.

## Testing Plan (v0.2 - manual, per the guide)

1. Apply migration to a fresh scratch DB -> all 6 tables exist (`.tables`).
2. Run the migration runner again -> no error, nothing re-applied (idempotent).
3. Run seed -> insert sample clients and services.
4. Generate tasks for July 2026 twice -> task count identical after both runs.
5. Run the Dashboard count query by hand -> counts match what the seed data implies (verify against a hand-written expected list).
6. Try inserting a task with a bogus `client_id` -> FK error (proves PRAGMA is on).
7. Try inserting a duplicate client/period/service task -> UNIQUE error.

Automated tests (pytest) enter at v0.4 when task-generation logic becomes real code.

## Risks

- SQLite FK enforcement forgotten on some connection -> mitigated by a single shared connection function that always sets the PRAGMA.
- Schema churn after dad's first real use -> expected; that's what numbered migrations are for. Migration 002 will happen, and that is normal.
- `documents.year`/`financial_year` duplicate what `document_date` implies -> accepted for MVP because dad searches by FY, and not every document has a full date. Flagged as possible cleanup later.

## Alternatives Considered

- **Four boolean service columns on `clients`** instead of `client_services` - rejected: every new service becomes a schema migration; can't hold per-service notes.
- **Lookup tables for enums** (service_types, statuses) - rejected for MVP: adds joins everywhere for values that change ~never; CHECK constraints give the same integrity.
- **Storing pending counts on periods** - rejected: derived data drifts; computing is instant at this scale.
- **A generic `tasks` table with a `type` field for future task kinds** - rejected: imaginary future problem (guide: no speculative machinery).
