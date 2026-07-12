# TaxDesk Tech Stack

## Current Decision

Decided in [docs/decisions/001-tech-stack.md](decisions/001-tech-stack.md) (2026-07-09):

- Python 3.
- FastAPI.
- SQLite.
- Jinja2 server-rendered templates.
- Raw SQL via the standard-library `sqlite3` module (no ORM initially).
- Hand-written, numbered SQL migration scripts.

Initial dependencies: `fastapi`, `uvicorn`, `jinja2`. Nothing else without the dependency justification from the engineering guide.

## Why This Stack

### Python + FastAPI

Every HTTP request and response is visible and explainable. No build step, no code generation.

### SQLite + raw SQL

SQLite is a single-file database: dad's office data lives in one local file with no server. Raw SQL keeps Nikhil directly in contact with queries, joins, and schema evolution - the fundamentals this project exists to teach.

### Jinja2 templates

Plain server-rendered HTML keeps the UI layer boring and debuggable. Interactivity libraries (HTMX or similar) are a separate future dependency decision, only if a real workflow demands them.

### Local Browser App First

Start with a localhost app before any packaging. This avoids installer complexity while dad tests the workflow.

## What Not To Add Yet

- React / Next.js / any JS framework.
- ORM or migration framework.
- Supabase.
- Clerk.
- Stripe.
- Cloud Postgres.
- Docker.
- Kubernetes.
- Background job systems.
- Vector database.
- AI SDKs.

## Existing Repo Note

The older Python file-indexer direction was removed from the repo in July 2026. This decision returns to Python, but for the compliance tracker - not the old indexer roadmap.

Do not mix stacks accidentally.

## AI Later

When AI becomes justified by usage, possible stack additions:

- File indexing module.
- PDF/text parser.
- Embedding provider.
- Local vector store or SQLite-based retrieval.
- RAG answer generation with citations.
- Tool-calling assistant over structured compliance data.
