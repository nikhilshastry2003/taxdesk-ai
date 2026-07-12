# TaxDesk Folder Structure

## Documentation-First Structure

Current target:

```text
taxdesk-ai/
  README.md
  TAXDESK_AI_ARCHITECTURE.md
  taxdesk-command-center-demo.html
  docs/
    vision.md
    requirements.md
    architecture.md
    tech-stack.md
    roadmap.md
    folder-structure.md
    engineering-journal.md
    engieering_guide.md
    decisions/
      001-tech-stack.md
```

## Future App Structure

Stack decided in `docs/decisions/001-tech-stack.md`: Python + FastAPI + SQLite.

Draft layout (finalized in the v0.2 data model design note):

```text
taxdesk-ai/
  app/
    main.py            # FastAPI entry point
    routes/            # one module per page area
    services/          # domain logic (task generation, pending counts)
    db/
      migrations/      # numbered SQL scripts
      queries.py       # raw SQL access functions
    templates/         # Jinja2 pages
    static/            # css, minimal js
  tests/
  docs/
  pyproject.toml
```

## Folder Rules

- Do not create folders before they are needed.
- Do not add infrastructure folders just to look professional.
- Every folder should have a clear responsibility.
- Keep MVP code easy to navigate.

## Existing Static Demo

`taxdesk-command-center-demo.html` is a prototype, not the final app architecture.

Use it to understand screens and workflow. Do not treat it as production code.

