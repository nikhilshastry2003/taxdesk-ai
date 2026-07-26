# TaxDesk Code Map

Open any source file side by side with its section here to know why the
file exists, what it does, and where the deeper explanation lives.

Rule: every PR that adds or reshapes a file updates this map.

---

## pyproject.toml

Why it exists: the project's identity card and its dependency list.
What it does: names the project, pins the 4 runtime dependencies and
pytest for development, and configures pytest paths.
Deeper story: ADR 001 in docs/decisions, journal 2026-07-26.

## app/main.py

Why it exists: something must assemble the web app out of its parts.
What it does: builds the FastAPI app, runs database migrations once at
startup so opening the app is all a user ever does, and plugs in the
four route modules.
Deeper story: journal 2026-07-26, first entry.

## app/deps.py

Why it exists: pieces every route module needs, kept in one place.
What it does: holds the Jinja2 template engine, decides which database
file to use (TAXDESK_DB env var for tests, taxdesk.db otherwise), and
gives each web request its own connection that commits only on success.
Deeper story: journal 2026-07-26, first entry.

## app/db/migrations/001_initial_schema.sql

Why it exists: the approved data model as executable SQL, structure in
git while data stays local.
What it does: creates the 6 tables with every rule baked in, foreign
keys, allowed values, and the UNIQUE constraint that makes duplicate
tasks impossible.
Deeper story: design note 001, journal 2026-07-13.

## app/db/migrate.py

Why it exists: migration files do nothing by themselves, something must
apply each one exactly once per database.
What it does: connect() is the only sanctioned way to open the database
(foreign keys on, rows by name). migrate() applies pending .sql files in
numbered order and records them in the schema_migrations logbook.
Deeper story: journal 2026-07-13, the runner Q and A.

## app/db/queries.py

Why it exists: one boundary where ALL of the app's SQL lives, routes
never write SQL themselves.
What it does: small typed functions for settings, clients, services,
periods, tasks, and the pending counts and lists behind Dashboard and
Priority. Dashboard and Priority share these functions, which is why
their numbers can never disagree.
Deeper story: journal 2026-07-26 entries one and three.

## app/db/seed.py

Why it exists: pages cannot be built or tested against empty tables.
What it does: fills a development database with 6 fake clients, their
services, July 2026, generated tasks, and a couple of interesting
statuses. Runs only on a developer laptop, never on the office machine.
Deeper story: journal 2026-07-17 seed questions.

## app/services/generation.py

Why it exists: task generation is real business logic, kept free of
HTTP so tests can call it directly.
What it does: computes the financial year, holds the DUE_DAY_RULES
placeholder (all None until dad's answers), and creates a period's
missing tasks idempotently.
Deeper story: design note 003, journal 2026-07-26 second entry.

## app/routes/onboarding.py

Why it exists: dad's clients already exist as folders, the app should
learn them instead of making him type.
What it does: saves the root folder setting, lists its subfolders as
candidates, and creates a client for each folder dad confirms, ignoring
names that are not real subfolders.
Deeper story: design note 002, journal 2026-07-26 first entry.

## app/routes/clients.py

Why it exists: the client registry pages.
What it does: the home redirect, the client list, the client detail
page with its pending tasks for the period in context, and saving the
service checkboxes where unticking deactivates but never deletes.
Deeper story: design notes 002 and 004.

## app/routes/periods.py

Why it exists: months and their tick lists, the Excel replacement.
What it does: create a period, show its tasks grouped by service,
generate missing tasks, flip task statuses with an honest completion
trace, and close or reopen the month. Closed periods refuse writes.
Deeper story: design note 003, journal 2026-07-26 second entry.

## app/routes/dashboard.py

Why it exists: the glance pages, dad's morning question answered.
What it does: Dashboard shows pending counts per service, the total,
and clients with pending work. Priority lists the same rows grouped by
service with search, and filtered to one service it doubles as the EPF
or ESI page. Both read only.
Deeper story: design note 004, journal 2026-07-26 third entry.

## app/templates/

Why it exists: the HTML the pages render, one file per page.
What it does: base.html is the shared frame with the nav, the others
fill its content block, onboarding, clients, client_detail, periods,
period_detail, dashboard, priority. Values are auto escaped by Jinja2.
Deeper story: journal 2026-07-26 first entry, templating Q and A.

## tests/

Why it exists: the logic worth trusting is the logic that is tested.
What it does: conftest.py gives every test a fresh migrated database in
a temp folder. test_generation.py covers generation and due dates,
test_task_status.py covers status traces, test_dashboard.py covers
counts, search, defaults, and the mirror guarantee between Dashboard
and Priority.
Deeper story: journal 2026-07-26 second and third entries.

## taxdesk.db (not in git)

Why it exists: the actual database, created on first run.
What it does: holds all real data. Gitignored on purpose, structure
travels through migrations, data never leaves the machine.
Deeper story: journal 2026-07-13, why the db file is not committed.
