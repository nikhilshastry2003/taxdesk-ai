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

---

## PR 20, numbered migrations and the settings table

Purpose: give schema changes a future, and give onboarding the one
configuration value it needs, somewhere to keep the root folder.

What changed: `schema.sql` moved to
`database/migrations/001_schema.sql`, the runner applies every
pending numbered file in order, `002_settings.sql` adds a single row
SETTINGS table, tests for both.

Why this way: a generic key value settings table was proposed and
rejected on review, no evidence demanded it. Exactly one
configuration value exists in the product brief, so the table is one
typed row, ID checked to 1 so a second row is impossible, ROOT_FOLDER
NOT NULL so it can never be saved empty. A future value is a
migration adding a column, and migrations are now cheap by
construction. Renaming schema.sql was done now because zero real
databases exist, the only moment such a rename is free.

How it works: the runner reads the logbook, applies each unrecorded
file from `database/migrations/` in filename order, then ensures
required services. No SETTINGS row means the app is not configured,
onboarding creates the row when the practitioner picks the root
folder.

Review catch, transaction safety. The first version claimed one
commit protected each migration and its record, but executescript
commits on its own, proven by probe, so a crash between apply and
record could leave a migration applied but unrecorded, and the rerun
would crash into existing tables. The fix wraps each file and its
record in one real SQLite transaction, BEGIN and COMMIT carried
inside the executed script, rollback on failure, with a test that
breaks a migration halfway and proves neither its tables nor its
record survive.

---

## PR 21, the application skeleton

Purpose: establish the application layer's shape before any feature,
so every future page has an obvious home and the browser reaches
SQLite only through HTTP.

What changed: the app package, main.py building the app around one
database path, deps.py handing each request its own connection,
routes/health.py as the only endpoint, six tests, fastapi and uvicorn
pinned as the first runtime dependencies, httpx2 dev pinned for the
test client.

Why this way: create_app takes the database path as an argument, so
tests build real apps over temp databases with no configuration
system. Connections stay scoped to one request, opened from the
single sanctioned connect(), which gained check_same_thread off
because FastAPI may touch a request's connection from different
thread pool threads, safe exactly because a connection never serves
two requests. Startup runs migrations through lifespan and closes its
connection, requests never share it. The health route returns exactly
one field, ok, and a test enforces key for key equality so nothing
can quietly join the response later. Binding stays 127.0.0.1 by
uvicorn default, localhost IS the security boundary.

How it works: browser to uvicorn on localhost, FastAPI matches the
route, get_db yields a fresh connection from the app's database path,
the route proves the spine with SELECT 1 and answers ok, teardown
closes the connection. Startup applied pending migrations before the
first request was ever accepted.

---

## PR 22, onboarding

Purpose: the first real feature, the practitioner's folders become
clients, with an explicit confirmation between discovery and
creation.

What changed: the onboarding page and its two POST routes,
database/queries.py born with the four functions the flow needs, the
first templates, jinja2 and python-multipart pinned, get_db grown to
commit on success and roll back on failure now that writes exist,
row access by name added to connect(), eleven new tests.

Why this way: no automatic insertion ever, because in a system that
never deletes, the moment before a row exists is the only cheap
place for judgment. The filesystem is read only here, onboarding
never touches the practitioner's real folders. The confirm handler
trusts nothing from the browser, it rescans the real root at
confirmation time and accepts only names that match actual
subfolders, so traversal names die silently, and the UNIQUE rule on
folder paths stays the final guard beneath it. Changing the root
never rewrites existing client paths, path repair is a named future
feature, not an onboarding side effect.

How it works: GET shows the root form, then discovery, immediate
subfolders only, files and hidden folders excluded, existing clients
marked, new folders ticked, and a button that says exactly what it
will do, Add N clients. POST root validates and upserts the single
SETTINGS row, 303. POST confirm derives the valid set from disk,
creates the intersection with the submission, 303. Reruns show
already added and create nothing new, proven by test and by a live
HTTP smoke run.

One test side find, httpx2 silently treats a list of tuples as raw
upload content instead of form fields, repeated fields must be sent
as a dict with a list value. The app code was never wrong, the test
encoding was.
