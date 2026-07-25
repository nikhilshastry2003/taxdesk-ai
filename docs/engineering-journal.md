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
