# TaxDesk Engineering Journal

Use this file to record what was learned while building TaxDesk.

The goal is not just to finish the product. The goal is to become a better engineer while building it.

## Entry Template

```text
Date:

What we built:

What I learned:

Decision made:

Mistake or confusion:

Question to revisit:

Next step:
```

---

## 2026-07-05

What we built:

- Started documentation-first project setup.
- Defined TaxDesk as a local-first compliance command center.
- Confirmed MVP should not start with AI/RAG/agents.

What I learned:

- A useful product can become an AI product later.
- The first milestone should solve dad's real workflow, not create an impressive architecture.

Decision made:

- Dashboard is the source of truth.
- MVP tracks only GSTR-3B, GSTR-1, EPF, and ESI.
- Priority mirrors Dashboard.
- Documents search stays.
- Assistant/chat and RAG are later.

Next step:

- Review docs.
- Decide the implementation stack before writing app code.

---

## 2026-07-12

What we built:

- Created the personal GitHub repo and landed the compliance pivot on it (PRs #1, #2).
- Decided the stack: Python + FastAPI + SQLite, raw SQL, Jinja2 templates (ADR 001).
- Wrote and approved Design Note 001: the data model, root-folder mapping, and confirm-first proof detection.

### How we designed the data model

We did not start from tables. We started from the one question TaxDesk must answer every morning:

```text
Which clients have pending GSTR-3B, GSTR-1, EPF, or ESI work, and where is the proof?
```

The nouns in that question became the entities. An entity is a thing the business tracks; each entity becomes a table, each row one real instance:

- **clients** - the parties dad works for. Holds identity plus `folder_path`, because every client already has a folder on disk.
- **client_services** - which of the 4 compliance services apply to each client. This exists as its OWN table (not four yes/no columns on clients) so that adding a fifth service someday is a new row, not a schema change. That separation is called normalization.
- **compliance_periods** - one row per month being tracked. Exists so tasks can point at "July 2026" instead of every task repeating month/year/FY strings.
- **compliance_tasks** - the heart of the model. One row = one client x one service x one period, with status and proof fields. Every page (Dashboard, Priority, Client, EPF, ESI) is just a different query over this single table - which is WHY Priority can never disagree with Dashboard.
- **documents** - saved file links for search, independent of tasks.
- **settings** - key-value rows for app-level facts, first one being `root_folder`.

### How the entities relate (primary keys and foreign keys)

Every table gets `id INTEGER PRIMARY KEY`. A primary key uniquely identifies a row. We use a plain integer id instead of, say, the client name, because names get respelled and edited - the id never changes, so everything else can safely point at it.

A foreign key is a column that holds another table's primary key, forming the relationship:

- `client_services.client_id -> clients.id` - one client HAS MANY services (one-to-many).
- `compliance_tasks.client_id -> clients.id` and `compliance_tasks.period_id -> compliance_periods.id` - a task is the meeting point of client x service x period.
- `documents.client_id -> clients.id`, with `period_id` allowed to be NULL because not every saved file belongs to one month.

The database enforces these: it refuses a task pointing at a client id that does not exist. SQLite gotcha we must remember: foreign key enforcement is OFF by default - every connection has to run `PRAGMA foreign_keys = ON`, so our db module will do it in exactly one shared place.

### Constraints as business rules

The most important design trick in the whole schema:

- `UNIQUE (client_id, period_id, service_type)` on compliance_tasks means the DATABASE makes duplicate task generation impossible. Even if the generation code runs twice, the second insert has nowhere to go. A rule enforced by the schema cannot be broken by buggy code; a rule enforced only in code can.
- `CHECK (status IN ('pending','done','not_applicable'))` acts as a lightweight enum - a typo like 'Done' is rejected at write time.
- `UNIQUE (month, year)` on periods - July 2026 can only exist once.

### The SQL queries the model must serve, and why

We designed the tables by checking they could answer the real screens:

1. Dashboard counts - `SELECT service_type, COUNT(*) ... WHERE period_id = ? AND status = 'pending' GROUP BY service_type`. Counts are COMPUTED at read time, never stored in a column, because a stored count can drift from the truth; a computed one cannot.
2. Priority / EPF / ESI lists - same WHERE clause, `JOIN clients` to show names instead of ids. Same filter = same truth as Dashboard, structurally.
3. Monthly generation - `INSERT OR IGNORE INTO compliance_tasks ... SELECT ... FROM client_services WHERE active = 1`. One set-based statement creates a task for every client's active service; `OR IGNORE` plus the UNIQUE constraint makes re-running it harmless (idempotent).
4. Confirmation inbox - `WHERE proof_status = 'detected'` lists files the scanner found, waiting for dad's one-click confirm.

### Folder mapping design

Three path fields, three different jobs: `settings.root_folder` (dad picks once), `clients.folder_path` (filled automatically by discovering subfolders of the root), `compliance_tasks.proof_file_path` (the exact file proving one task, suggested by the scanner or linked manually).

Generalization rule we settled on: the schema holds what is universal to every tax office (clients, services, periods, tasks, proofs). What varies per office - folder layout, naming habits - lives as DATA (settings rows, future pattern rows), never as schema changes. Another office = different rows, same schema, same code.

What I learned (beyond the above):

- Commit identity (user.name/email) and push credentials are two separate systems; repo-local config overrides global.
- `git log` shows committed history; `git status` shows the working tree - they answer different questions.

Decision made:

- Proof auto-detection is in MVP scope with a confirm-first policy (no silent auto-done).
- Dad maps one root folder once; TaxDesk discovers client folders from it.
- task_label dropped from the schema: never store what you can derive.

Mistake or confusion:

- The gh auth browser page said "connected" but the CLI never saved the token because the terminal process had closed - had to re-run the login.
- `git commit` without `-m` dropped me into nano unexpectedly; an empty message aborts the commit.

Question to revisit:

- What do dad's real proof filenames look like? Need dir listings of 2-3 client folders (blocks Design Note 002).
- Due-date rules per service - dad is the source, do not hardcode assumptions.

Next step:

- Merge the design-note PR, then implement v0.2: migration 001, migration runner, seed data. Stdlib only.

---

## 2026-07-13

What we built:

- `app/db/migrations/001_initial_schema.sql` - our approved tables, written as real SQL.
- `app/db/migrate.py` - a small program (~50 lines) that runs migration files. No libraries needed.
- `.gitignore` + `*.db` - the database file stays on the computer, never goes to GitHub.

### Q: What is a migration?

A migration is a numbered SQL file. Each file makes one change to the database structure.

We never change the database by hand. We add a new file instead. Any computer can then build the exact same database by running the files in order: 001, then 002, then 003...

In TaxDesk: `001_initial_schema.sql` builds our 6 tables. The next change will be a new file (002). We never edit 001 again, because it has already run on real databases.

Why we need this: `taxdesk.db` will hold dad's client data, so it stays on his computer. But the table structure must reach every computer. Migrations solve this: structure goes to GitHub as files, data stays local.

### Q: What is the runner?

The runner is `migrate.py`. Its job: run each migration file once, in the right order, and remember what it already ran.

How it remembers: it writes the name of every finished file into a table called `schema_migrations`, inside the database itself. On every run it asks one question: "which files are new?" and runs only those.

Why we wrote our own: tools like Prisma or Alembic do this for you, but they hide how it works. Ours is 50 lines, and we understand every line.

### Q: What happens when we run it?

1. It opens `taxdesk.db`. If the file does not exist, SQLite creates it.
2. It turns on foreign key checking (SQLite keeps this off unless you ask).
3. It reads the logbook: which files were already run?
4. It runs the new files. After each one, it writes the name into the logbook and saves.
5. Run it again: nothing is new, so it prints "nothing to apply". It is always safe to run.

### Q: Why put rules inside the database instead of Python code?

Because the database checks its rules on EVERY write, no matter which code is writing. A Python check can be skipped if someone forgets it in one place. The database never forgets.

We proved it today with real inserts:

- A task pointing to a client that does not exist -> rejected.
- A status with wrong spelling ('Done') -> rejected.
- The same task added twice -> rejected. So duplicate tasks can never happen, even if our code has a bug.

What I learned:

- Opening a SQLite database and creating it are the same act - connect() makes the file if it is missing.
- `Path(__file__)` means "the folder where this script lives" - it makes the script work from any directory.
- Passing a different database path as an argument lets us test on a throwaway file, never on real data.
- Migration tools are not magic: a folder of files, a logbook table, and a "what is new?" check.

Decision made:

- Database files (`*.db`) never go to git: structure is committed, data is not.
- Every part of the app must open the database through `connect()` - it is the one place that turns foreign keys on.

Mistake or confusion:

- The first draft of the migration was written from memory and had a wrong value ('auto_confirmed' instead of the approved 'scan_confirmed'). Caught by re-reading the design note. Lesson: always copy from the source of truth, never from memory.

Question to revisit:

- SQLite cannot change existing tables freely. Before migration 002, learn the rebuild trick: make a new table, copy the data over, drop the old one, rename.

Next step:

- Seed script: sample clients, services, the July 2026 period, and task generation running for real.

---

## 2026-07-17

What we did:

- Added `docs/agents.md`, the standing rules for coding, style, docs, and chat.
- Reviewed `migrate.py` and the schema against it, then refactored `migrate.py` to match. No schema changes.

### Q. What changed in migrate.py

- Every function now declares its types, what goes in and what comes out. A type annotation is a contract at the boundary. The tooling can check it and the next reader gets it for free.
- Comments that repeated the code were deleted. The ones that stayed say only what the code cannot. They explain why the foreign key PRAGMA lives in connect() and why we record and commit right after executing a migration.
- migrate() now returns early when nothing is pending. Edge cases exit at the top, the real work sits flat at the bottom.

### Q. Why did the schema pass with no changes

Two reasons. First, migration 001 has already run on databases, so it is frozen. Any real change would be a new file, 002. Second, the review found nothing broken. Two things were noted for later, not fixed now.

- `updated_at` does not update itself. SQLite has no automatic mechanism for it, so the app must set it on every UPDATE.
- There are no indexes yet. With hundreds of rows they are pointless, and adding them today would be building for an imagined future.

Decision made:

- In code, comments follow agents.md and say only what the code cannot. The teaching explanations live here in the journal instead of inside the code.

### Q. What is seed data

A script that fills the development database with fake clients, `app/db/seed.py`. Pages can then be built against realistic rows instead of empty tables. It runs only on the developer laptop, by hand. The office machine starts empty and fills through onboarding, it never runs seed.

### Q. What did seeding prove

- Six fake clients with mixed services produced 13 tasks from one INSERT OR IGNORE SELECT, the exact query the app will use for monthly generation in v0.4.
- The whole script ran twice and gave identical counts, 12 pending. The UNIQUE constraint blocked the duplicates, not Python code.
- The Dashboard count query returned 3 pending per service, real numbers from real rows, before any UI exists. The data model answers its core question.
- One task marked done and one proof marked detected, so every screen state already has data waiting for v0.3.

Also cleared a doc debt. Both architecture files now match the approved schema, task_label removed, settings table added, a promise from design note 001 that had slipped.

Next step:

- v0.3, first FastAPI pages and client onboarding, on the go signal.

---

## 2026-07-26

What we built:

v0.3 client management, the first web code. A FastAPI app with onboarding, a client list, client detail, and service configuration. Design note 002 approved first, then implemented.

### Q. What is each new file for

```text
pyproject.toml                  project identity plus the 4 pinned dependencies
app/main.py                     builds the FastAPI app, runs migrations at startup, plugs in the routes
app/deps.py                     shared pieces, the template engine and the per request db connection
app/db/queries.py               every SQL statement the web app runs, as typed functions
app/routes/onboarding.py        root folder form, discovery, confirm
app/routes/clients.py           client list, client detail, service saving
app/templates/base.html         the shared page frame every page extends
app/templates/onboarding.html   the onboarding page
app/templates/clients.html      the client list page
app/templates/client_detail.html one client with its service checkboxes
app/__init__.py                 empty, see below
app/db/__init__.py              empty, see below
app/routes/__init__.py          empty, see below
```

### Q. Why do the empty __init__.py files exist

They turn a plain folder into a Python package, which is what makes dotted imports work. `from app.db import queries` only resolves because `app/` and `app/db/` each contain an `__init__.py`. Without them Python does not treat the folders as importable code.

They are empty because marking the folder is their entire job. Code inside them runs on import, which is a place bugs love to hide, so the convention is to keep them empty unless there is a strong reason not to.

### Q. What is FastAPI and what runs it

FastAPI receives a browser request, finds the function registered for that path, and turns the function's return value into a response. It cannot listen on a network port by itself. That job belongs to uvicorn, the server process that accepts connections and hands each request to FastAPI. They are the standard pairing.

```bash
venv/bin/uvicorn app.main:app --reload
```

### Q. What is a route

One URL path mapped to one Python function. The app has seven.

### Q. Where did we use GET and POST, and why each

GET means read. It must never change data, so it is safe to refresh, bookmark, or repeat. POST means write. The browser itself treats them differently, it warns before resending a POST but repeats a GET silently, which is exactly why a write must never hide behind a GET.

Our four GET routes, all pure reads:

- `GET /` decides where to send you, onboarding when no root folder is saved yet, otherwise the client list
- `GET /onboarding` shows the root folder form and the discovered subfolders
- `GET /clients` shows the client list
- `GET /clients/{id}` shows one client with its service checkboxes

Our three POST routes, all writes:

- `POST /onboarding/root` saves the root folder path into settings
- `POST /onboarding/confirm` creates a client row for each ticked folder
- `POST /clients/{id}/services` saves the service ticks for one client

Every POST finishes with a redirect to a GET page, the post redirect get pattern. After a save the browser lands on a plain readable page, so refreshing rereads instead of resubmitting the form.

### Q. Why are some route functions async

Python has two kinds of functions here. A plain def blocks its thread until it finishes. An async def can pause at an await and let the server do other work while it waits.

Our GET routes are plain def, FastAPI runs them in a thread pool automatically. The three POST routes are async def for one concrete reason, reading a submitted form is `await request.form()`, because the body arrives over the network in pieces and awaiting lets the server work while it completes.

Rule of thumb we follow, async only where something is genuinely awaited, plain def everywhere else. No async for fashion.

### Q. How do pages get their HTML

Jinja2 templates. base.html holds the shared frame, each page fills in its content block. Every value dropped into a template is escaped automatically, so a client named `<script>` renders as harmless text instead of running. Injection is closed by default, not by our discipline.

### Q. Where does SQL live

In exactly one file, app/db/queries.py, as small typed functions. Routes call functions and never write SQL. Database code never sees HTTP. That one boundary is the main architecture lesson of this milestone, each layer can change without touching the other.

### Q. What did the first test run catch

Two real bugs, before any human ever clicked the app.

- Form posts crashed. The installed starlette refuses to parse any form without the python-multipart library. My assumption that simple forms worked without it was wrong. It came in as a justified fourth pinned dependency, and the design note records the deviation.
- Database calls crashed across threads. FastAPI runs plain def code in a thread pool and async code on its main loop, so a connection born on one thread got used on another. SQLite blocks that by default. The fix is the official FastAPI pattern, check_same_thread off, safe because a connection never leaves its one request.

The lesson, a written test plan run honestly finds the bugs the author's assumptions hid.

What I learned:

- The onboarding confirm endpoint validates that submitted folder names really are subfolders of the root. Form input crosses a trust boundary even on localhost.
- Unticking a service updates active to 0 and the row survives, verified by direct query. Deactivation is not deletion, now visible in real data.
- Rerunning onboarding created zero duplicate clients, the same INSERT OR IGNORE idea that protects tasks.

Decision made:

- python-multipart joins the pinned dependencies, required by starlette for all form parsing.
- Connections open with check_same_thread off, the documented FastAPI and SQLite pattern.

Mistake or confusion:

- Designed with three dependencies, reality needed four. The miss was found by running the test plan, not by a user, which is the system working.

Question to revisit:

- Dad pastes his root folder path as text for now. Whether he gets a real folder picker is a packaging time question.

Next step:

- Side task, dir listings of 2 or 3 real client folders from dad.
- v0.4, period selector and monthly task generation.

---

## 2026-07-26, second entry

What we built:

v0.4 task generation, the milestone that functionally replaces the Excel sheet. Periods page, create a month with its financial year computed, generate tasks, mark them done or not applicable, close a finished month. Plus the project's first automated tests.

### Q. What is new in the file map

```text
app/services/generation.py   generation and financial year logic, no HTTP in it
app/routes/periods.py        period pages, generate, close, task status
app/templates/periods.html and period_detail.html
tests/conftest.py            shared test fixtures
tests/test_generation.py     7 generation tests
tests/test_task_status.py    3 status tests
```

### Q. Why does app/services exist now, and what is a pure logic layer

Generation logic could have lived inside the route function. It did not, because logic buried in a route can only be tested by faking a whole web request. In its own module with plain functions over a database connection, a test imports it and calls it directly. Routes stay thin, they parse the request, call the service, redirect. This is the layering idea again, web code, logic, SQL, each in its own file.

### Q. What is pytest and what is a fixture

pytest finds every function named `test_*` and runs it, a failed assert means a failed test. A fixture is a named piece of setup a test asks for by parameter name. Our `conn` fixture builds a fresh database in a temp folder and runs migrations on it, so every single test starts from a clean, real schema and the actual taxdesk.db is never touched.

```bash
venv/bin/pytest -q      # 11 passed in 0.64s
```

### Q. How are due dates handled when dad has not answered yet

A placeholder, exactly as decided. One mapping in code, `DUE_DAY_RULES`, every service None today. Generation fills a due date only where a rule exists, so all dates are empty for now, shown as a quiet dash. One test proves the future too, it sets a rule the way dad's answer will, regenerates, and watches only that service's dates backfill. The mechanism is live, only the numbers are missing.

### Q. How is the financial year computed

April to March. Month 4 or later belongs to the year that starts then, month 1 to 3 belongs to the year before. July 2026 gives 2026-27, February 2026 gives 2025-26. Computed from month and year, never typed, never stored wrong.

### Q. What does closing a period do

Sets its status to closed, and every write route checks it first. Generation and status changes against a closed month bounce back with a visible message instead of writing. History gets frozen on purpose, reopen exists for genuine corrections.

What I learned:

- rowcount after INSERT OR IGNORE counts only rows actually inserted, which is how generate can report 13 new, then 0 new.
- monkeypatch in a test can simulate a future configuration without editing the code, which is how the due date backfill is already proven.
- A test suite plus a manual click through catch different things, the suite locks logic, the click through catches wiring, templates, and redirects.

Decision made:

- pytest 9.1.1 pinned as the first dev only dependency, tests run on temp databases through the conftest fixture.
- Due dates stay NULL until dad's rules land, backfill is one edit per service plus one generate click.

Mistake or confusion:

- None new this milestone. The v0.3 lessons, test before shipping and copy from the source of truth, were simply applied.

Question to revisit:

- The following month assumption inside due date computation must be confirmed with dad along with the day numbers.

Next step:

- v0.5, Dashboard and Priority, both reading the same pending tasks these pages now create.

---

## 2026-07-26, third entry

What we built:

v0.5, the Dashboard and Priority pages. Opening TaxDesk now lands on the glance page, four pending counts, a total, and the clients that still owe work. Priority shows the same rows as a searchable working list, and filtered to one service it doubles as the EPF or ESI page.

### Q. How can two pages be guaranteed to agree

They run the same query functions with the same conditions. The Dashboard counts rows that Priority lists, nothing is stored, nothing can drift. And it is no longer a promise, one pytest test computes the counts, lists the rows per service, and asserts they are equal. A future change that breaks the mirror breaks the build.

### Q. What is a query parameter and how do we use it

The part of a URL after the question mark, `/priority?service=EPF&q=kumar`. The page reads them as filters, period, service, search text. That is how one template serves five views, full Priority, four service pages, with zero JavaScript. Anything invalid in them is ignored and the page falls back to sane defaults.

### Q. How does search work without JavaScript

A plain GET form. The browser puts the text into the URL as `q=...`, the route passes it into SQL as `name LIKE ?` with the text parameterized, never spliced into the string. LIKE with COLLATE NOCASE matches fragments ignoring case, so "kumar" finds "Kumar Textiles".

### Q. What changed in how functions are written

Every function now carries a docstring a first time reviewer can follow, what it exactly does, then an In line and an Out line in plain words. Settled today after a few rounds, the bar is, someone opening the file cold understands the ins and outs without another file open.

### Q. What is a JOIN, from first principles

Tables stand alone and know nothing about each other. A task row stores `client_id 7`, a number, not a name, because names change and ids do not. So how does a page show "Kumar Textiles" instead of "client 7"? A JOIN. `JOIN clients c ON c.id = t.client_id` tells the database, for every task row, find the client row whose id matches, and glue the two into one wider row. That is the whole idea, matching rows across tables by a shared key. Foreign keys make the link trustworthy, joins make it readable.

### Q. What does GROUP BY actually do

Rows go in, buckets come out. `GROUP BY service_type` throws every pending task into one bucket per service, and `COUNT(*)` measures each bucket. Many rows collapse into one summary row per group. This is aggregation, and it is why the Dashboard stores nothing, it re-summarizes the truth on every glance. A stored summary can lie, a computed one cannot.

### Q. Why do some redirects say 302 and others 303

Both tell the browser, go to this other page. 302 is the plain one, we use it for simple reads like the home page forwarding to the Dashboard. 303 carries one extra instruction, fetch the next page with GET no matter what you just did. That matters exactly once, after a form POST, and it is the precise letter of the post redirect get pattern, the reason refresh never resubmits a form.

What I learned:

- A product requirement can live as a test. "Priority must exactly mirror Dashboard" is now code that fails loudly, which is stronger than any promise in a document.
- Computing counts at read time is what made this milestone almost free, two pages and zero migrations, because the data model carried the weight.
- 18 tests now run in about a second, fast enough to run after every change without thinking.

Decision made:

- Dedicated EPF and ESI pages are Priority filtered by service, one template, four views, nothing extra to maintain.
- Dashboard stays read only by rule, marking done happens on the period page.

Mistake or confusion:

- None new in the code. The docstring style took three attempts to land because I kept guessing the depth instead of asking for an example of what Nikhil wanted to read.

Question to revisit:

- Whether the Dashboard should someday show due date urgency, colors for near deadlines, once real due days exist.

Next step:

- v0.6, Documents and the proof scanner, the beat Excel moment. Needs dad's folder listings at install time.

---

# Code Map, A Living Section

This part is reference, not diary. It gets updated in every PR that adds
or reshapes a file. Open any source file next to its entry here and you
should never need to ask what this is, what it calls, or who calls it.
The dated entries above teach the fundamentals behind each one.

## The one rule that organizes everything

Requests flow downward through three layers, and each layer only ever
talks to the one below it.

```text
routes (web code)  ->  queries / services (logic)  ->  sqlite (data)
```

Routes never write SQL. Queries never see HTTP. The database never
knows a web app exists. Every file below belongs to exactly one layer.

## How one page request flows, start to finish

```text
1. the browser asks for /dashboard
2. uvicorn, the server process, accepts the request and hands it to
   the FastAPI app that app/main.py built
3. FastAPI matches the path and calls dashboard() in
   app/routes/dashboard.py
4. FastAPI sees the route wants a database connection and calls
   get_db() in app/deps.py to open one just for this request
5. the route calls query functions in app/db/queries.py, which run
   SQL against taxdesk.db and return rows
6. the route hands the rows to a template in app/templates/, Jinja2
   fills the HTML, the response travels back the same road
```

## How startup flows

```text
venv/bin/uvicorn app.main:app
 -> Python imports app/main.py, which imports the four route modules
 -> lifespan() in main.py runs once, it calls connect() and migrate()
    from app/db/migrate.py, so the database is created or upgraded
    before the first request
 -> the app starts answering
```

### pyproject.toml

Why it exists: the project's identity card and its dependency list.
What it does: names the project, pins the 4 runtime dependencies and
pytest for development, and configures pytest paths.
Deeper story: ADR 001 in docs/decisions, entry 2026-07-26.

### app/main.py

Why it exists: something must assemble the web app out of its parts.
What it does: builds the FastAPI app object, runs migrations once at
startup, and plugs in the four route modules.
Functions: lifespan() is the only one, it runs around the app's whole
life, migrations before the first request, nothing after.
Calls: connect() and migrate() from app/db/migrate.py, db_path() from
app/deps.py, and include_router() once per route module.
Called by: uvicorn, which imports app.main:app when you start the app.
Deeper story: entry 2026-07-26, first entry.

### app/deps.py

Why it exists: pieces every route module needs, kept in one place.
What it does: holds the shared template engine and hands out database
connections, one per web request.
Functions: db_path() picks the database file, the TAXDESK_DB env var
for tests, taxdesk.db otherwise. get_db() opens a connection for one
request, commits only if the route finished without an error, and
always closes it.
Calls: connect() from app/db/migrate.py.
Called by: every route function, FastAPI runs get_db() automatically
whenever a route declares Depends(get_db). main.py calls db_path() at
startup.
Deeper story: entry 2026-07-26, first entry.

### app/db/migrations/001_initial_schema.sql

Why it exists: the approved data model as executable SQL, structure in
git while data stays local.
What it does: creates the 6 tables with every rule baked in, foreign
keys, allowed values, and the UNIQUE constraint that makes duplicate
tasks impossible.
Deeper story: design note 001, entry 2026-07-13.

### app/db/migrate.py

Why it exists: migration files do nothing by themselves, something must
apply each one exactly once per database.
Functions: connect() is the only sanctioned way to open the database,
it switches foreign keys on and makes rows readable by column name.
applied_migrations() reads the logbook table. migrate() computes
pending files minus applied ones and runs each, recording it.
Calls: only Python's sqlite3 and pathlib, nothing of ours, this is the
bottom of the stack.
Called by: everyone. main.py at startup, deps.get_db() per request,
seed.py, and every test through the conftest fixture. Also runnable by
hand, python3 app/db/migrate.py.
Deeper story: entry 2026-07-13, the runner questions.

### app/db/queries.py

Why it exists: one boundary where ALL of the app's SQL lives, routes
never write SQL themselves.
Functions, grouped by what they manage:
- settings, get_setting() and set_setting(), read and write one
  key value row, like the root folder path
- clients, list_clients(), get_client(), create_client()
- services, active_services() reads a client's switched on services,
  set_service() switches one on or off without ever deleting
- periods, list_periods(), get_period(), create_period(),
  set_period_status(), and default_period() which picks the month
  pages show when none is chosen
- tasks, tasks_for_period() for the period page table, get_task(),
  set_task_status() which keeps the completion trace honest
- glance reads, pending_counts(), pending_tasks(), pending_clients(),
  client_pending_tasks(), the four behind Dashboard and Priority
Calls: nothing of ours, it only runs SQL through the connection it is
handed.
Called by: every route module, and the dashboard tests call the glance
reads directly.
Deeper story: entries 2026-07-26, first and third.

### app/db/seed.py

Why it exists: pages cannot be built or tested against empty tables.
What it does: fills a development database with 6 fake clients, their
services, July 2026, generated tasks, and a couple of interesting
statuses. Runs only on a developer laptop, never on the office machine.
Functions: main() runs the whole thing in order, seed_clients(),
seed_period(), generate_tasks(), mark_sample_statuses(), then
print_dashboard() as proof of life.
Calls: connect() and migrate() from migrate.py, then its own inserts.
Called by: nobody in the app, only a human typing
python3 app/db/seed.py.
Deeper story: entry 2026-07-17, seed questions.

### app/services/generation.py

Why it exists: task generation is real business logic, kept free of
HTTP so tests can call it directly.
Functions: financial_year() computes the April to March year text.
due_date_for() turns a service's due day rule into a real date, None
everywhere until dad's answers fill DUE_DAY_RULES. generate_tasks()
creates a period's missing tasks and backfills due dates where rules
exist.
Calls: nothing of ours, pure logic over the connection it is handed.
Called by: routes/periods.py when the generate button is clicked, and
directly by the generation tests.
Deeper story: design note 003, entry 2026-07-26, second.

### app/routes/onboarding.py

Why it exists: dad's clients already exist as folders, the app should
learn them instead of making him type.
Functions: onboarding_page() shows the form and the discovered
folders. save_root() checks the typed path is a real folder and saves
it. confirm_clients() creates a client per ticked folder, ignoring
names that are not real subfolders. folder_candidates() is the shared
helper that lists subfolders and marks which are already clients.
Calls: queries get_setting, set_setting, list_clients, create_client,
plus pathlib to walk the disk, and the templates from deps.
Called by: FastAPI for GET /onboarding, POST /onboarding/root, and
POST /onboarding/confirm.
Deeper story: design note 002, entry 2026-07-26, first.

### app/routes/clients.py

Why it exists: the client registry pages.
Functions: home() redirects / to the Dashboard, or to onboarding when
no root folder is saved yet. client_list() shows everyone.
client_detail() shows one client, its service ticks, and its pending
tasks for the period in context. save_services() writes the checkbox
form, on for ticked, off for unticked, never deleting.
Calls: queries get_setting, list_clients, get_client, active_services,
set_service, get_period, default_period, client_pending_tasks, and the
templates from deps.
Called by: FastAPI for GET /, GET /clients, GET /clients/{id}, and
POST /clients/{id}/services.
Deeper story: design notes 002 and 004.

### app/routes/periods.py

Why it exists: months and their tick lists, the Excel replacement.
Functions: period_list() shows every month plus the create form.
create_period() validates month and year, computes the financial year,
and creates or reuses the month. period_detail() shows the month's
tasks grouped by service. generate() creates missing tasks, refused
when the month is closed. toggle_close() freezes or unfreezes a month.
set_task_status() flips one task from the page buttons, refused on a
closed month or a bad value.
Calls: queries for periods and tasks, financial_year() and
generate_tasks() from services/generation.py, templates from deps.
Called by: FastAPI for GET and POST /periods, GET /periods/{id},
POST generate, POST toggle-close, and POST /tasks/{id}/status.
Deeper story: design note 003, entry 2026-07-26, second.

### app/routes/dashboard.py

Why it exists: the glance pages, dad's morning question answered.
Functions: pick_period() decides which month the page is about, the
URL first, the default period second. dashboard() gathers counts,
total, and the pending client list. priority() gathers the same rows
grouped by service, applies the service filter and the name search,
and filtered to one service it doubles as the EPF or ESI page. Both
pages are read only.
Calls: queries pending_counts, pending_tasks, pending_clients,
list_periods, get_period, default_period, and templates from deps.
Called by: FastAPI for GET /dashboard and GET /priority.
Deeper story: design note 004, entry 2026-07-26, third.

### app/templates/

Why it exists: the HTML the pages render, one file per page.
What it does: base.html is the shared frame with the nav, the others
fill its content block, onboarding, clients, client_detail, periods,
period_detail, dashboard, priority. Values are auto escaped by Jinja2.
Called by: routes hand each template a dict of values through
templates.TemplateResponse(), templates never call code, they only
display what they are given.
Deeper story: entry 2026-07-26, first, the templating question.

### tests/

Why it exists: the logic worth trusting is the logic that is tested.
What it does: conftest.py gives every test a fresh migrated database in
a temp folder. test_generation.py covers generation and due dates,
test_task_status.py covers status traces, test_dashboard.py covers
counts, search, defaults, and the mirror guarantee between Dashboard
and Priority.
Calls: migrate.py for the fixture database, then queries.py and
services/generation.py directly, skipping the web layer on purpose,
tests lock the logic, the manual click through checks the wiring.
Called by: venv/bin/pytest, which finds every test_ function itself.
Deeper story: entries 2026-07-26, second and third.

### taxdesk.db (not in git)

Why it exists: the actual database, created on first run.
What it does: holds all real data. Gitignored on purpose, structure
travels through migrations, data never leaves the machine.
Deeper story: entry 2026-07-13, why the db file is not committed.
