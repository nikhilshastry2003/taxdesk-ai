# TaxDesk AI

TaxDesk is a local-first compliance command center for small Indian tax practitioners.

The first design partner is Nikhil's dad. The first goal is to replace his Excel tick-mark checklist for monthly compliance work.

## MVP Scope

TaxDesk v1 focuses on:

- Dashboard as the single source of truth.
- Priority page that mirrors Dashboard pending data.
- Client page showing selected client's pending status.
- Documents page for local folder/file search.
- Pending compliance:
  - GSTR-3B.
  - GSTR-1.
  - EPF / ECR.
  - ESI Challan / Claims.

## Not In MVP

- SaaS auth/billing.
- Tally replacement.
- GST portal automation.
- OCR.
- Assistant/chat.
- RAG.
- Embeddings.
- Agents.
- Multi-agent systems.

## Current Files

- `taxdesk-command-center-demo.html` - static UI prototype.
- `TAXDESK_AI_ARCHITECTURE.md` - current product architecture.
- `docs/` - project documentation.

## Documentation

Start here:

- `docs/vision.md`
- `docs/requirements.md`
- `docs/architecture.md`
- `docs/tech-stack.md`
- `docs/roadmap.md`
- `docs/folder-structure.md`
- `docs/engineering-journal.md`
- `docs/engieering_guide.md`
- `docs/deep-dive.md` (also as `docs/deep-dive.pdf`)
- `docs/codebase-mastery.md` (also as `docs/codebase-mastery.pdf`)

## Next Milestone

Do not build UI first.

The next engineering milestone is:

```text
Client + compliance task data model
```

The stack is decided: Python + FastAPI + SQLite (see `docs/decisions/001-tech-stack.md`).

Before coding, write the schema/design note.
