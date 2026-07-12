# 001 - Implementation Stack For TaxDesk v1

Status: Accepted

Date: 2026-07-09

Decider: Nikhil (Tech Lead)

---

## Problem

TaxDesk v1 needs an implementation stack before the v0.2 data model design note can be written, because that note must name real files and tools.

The docs previously recommended Next.js + Prisma, but a recommendation is not a decision.

Criteria, in priority order:

1. Explainability - Nikhil can explain every layer without framework magic.
2. Learning value - the stack teaches durable engineering (SQL, HTTP, schema design).
3. Speed to a useful MVP for dad - 6 pages of CRUD over one SQLite file.
4. Future path - desktop packaging later, possible file-indexing work later.

Not criteria: performance, scale, popularity. One office, one user, one local database.

---

## Options

### Option A - Next.js + TypeScript + Prisma + SQLite

Advantages:

- One language across UI and logic.
- Prisma schema file is readable and close to the data model draft.
- Built-in migrations.
- shadcn/ui makes the 6 pages fast.
- Natural Tauri packaging path later.
- Matches the docs as previously written.

Disadvantages:

- Next.js concepts (server vs client components, app router) add weight unrelated to the product.
- Prisma hides SQL behind a generated client, which works against the learning goal.
- Heavy toolchain and build step for a purely local app.

### Option B - Python + FastAPI + SQLite (CHOSEN)

Advantages:

- Most transparent stack: every SQL query and HTTP request is visible.
- No build step, no code generation, no framework magic.
- Maximum engineering fundamentals per hour of work.
- Single process serving a local browser app.

Disadvantages:

- Building 6 interactive pages with server-rendered templates is slower than with a component library.
- Existing docs (tech-stack, folder-structure) were written for the JS path and needed updating (done alongside this note).
- If a rich React UI is ever needed, that becomes a second stack.

### Option C - Vite + React + Express + SQLite

Advantages:

- React without Next.js framework concepts.
- Same language throughout.

Disadvantages:

- The hand-wired plumbing (route handlers, build config) is boilerplate, not durable learning.
- Still leaves ORM-or-raw-SQL as a separate sub-decision.

---

## Decision

Python 3 + FastAPI + SQLite, with server-rendered Jinja2 templates for the UI.

Bundled sub-decisions (each revisitable via a new decision note):

- Database access: raw SQL through the standard-library `sqlite3` module. No ORM initially.
- Migrations: hand-written, numbered SQL scripts, applied in order. No migration framework initially.
- UI: plain server-rendered HTML via Jinja2. HTMX or any JS library is a separate future dependency decision, only if a real workflow demands interactivity.
- Initial dependencies limited to: `fastapi`, `uvicorn`, `jinja2`. Anything further needs the dependency justification from the engineering guide.

## Reason

The project's primary goal is Nikhil becoming a better engineer, not shipping fastest. Option B exposes the most fundamentals (SQL, HTTP, request/response, schema evolution) with the least magic.

Runner-up A lost because Next.js and Prisma insert concepts and generated code between Nikhil and the fundamentals, and the UI-speed advantage does not outweigh that for a 6-page MVP.

## Future Impact

- `docs/tech-stack.md` and `docs/folder-structure.md` updated to match this decision.
- A fresh `pyproject.toml` will be created when app scaffolding starts (the old one belonged to the removed file-indexer direction).
- UI development accepted as slower; dad-facing polish comes from working software, not component libraries.
- Desktop packaging (if ever needed beyond a local browser app) is a later decision note.
- If TaxDesk ever needs a rich client UI, that is a new decision note; the SQLite schema carries over regardless of stack.
