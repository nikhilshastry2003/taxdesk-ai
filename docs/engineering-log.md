# TaxDesk Engineering Log

One entry per merged PR, in order. Each answers four questions,
purpose, what changed, why this way, how it works. Every new PR adds
its entry in the same branch it ships on.

---

## PR 16, database schema

Purpose: give the product its data model, the tables and the rules
that make bad data impossible.

What changed: `database/schema.sql`, six tables, and
`docs/database-design.md` explaining the design.

Why this way: rules live in the schema as constraints, not in code,
because a constraint binds every writer forever while a code check
binds only the paths that remember it. The one rule the product
stands on, one client, one service, one month, at most one task, is a
UNIQUE constraint.

How it works: CLIENTS and SERVICES meet in the CLIENT_SERVICES
junction with an ACTIVE flag so switching off never erases history.
PERIODS is keyed naturally by year and month. TASKS carries a
surrogate id plus the four column UNIQUE. Foreign keys make orphan
rows impossible, CHECK constraints make illegal statuses impossible.

---

## PR 17, migration runner

Purpose: turn the schema file into real databases, identically, on
any machine, any number of times.

What changed: `database/migrate.py`, tests, `.gitignore`,
`pyproject.toml` with pinned pytest.

Why this way: SQLite keeps foreign key enforcement off per
connection, so connection creation is centralized in one connect()
function nothing else may bypass. Initialization must be rerunnable
without destroying data, so a logbook table records what has been
applied and the runner skips it forever after.

How it works: connect() opens or creates the file and switches
foreign keys on. initialize() checks the schema_applied logbook,
applies `schema.sql` only when unrecorded, and records it in the same
commit, so a crash between the two cannot desynchronize them.

---

## PR 18, seed data and required services

Purpose: give development a filled database, and settle where
required reference data lives.

What changed: `database/seed.py`, seed tests, REQUIRED_SERVICES moved
into `database/migrate.py` after review, seed made deterministic.

Why this way: review caught two real issues. Service INSERTs placed
in `schema.sql` were sealed the moment a database applied the file,
unreachable for future additions, so required services became a list
in the runner, ensured on every initialize with INSERT OR IGNORE. And
a `datetime('now')` in the seed broke the promise that rerunning
changes nothing, replaced by a fixed constant, with the idempotency
test strengthened from row counts to full state comparison.

How it works: three kinds of content, three homes. Structure in
`schema.sql`, required data as code in the runner, fake data in the
seed. The seed inserts five clients, twelve subscriptions with one
switched off, one month, and generates tasks with the same INSERT OR
IGNORE shape the app will later use.
