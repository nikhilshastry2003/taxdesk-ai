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
```

## Future App Structure

If we choose Next.js for implementation:

```text
taxdesk-ai/
  app/
    page.tsx
    priority/
    clients/
    documents/
    epf/
    esi/
  components/
    dashboard/
    priority/
    clients/
    documents/
    ui/
  lib/
    compliance/
    documents/
    db.ts
  prisma/
    schema.prisma
    seed.ts
  docs/
  tests/
```

## Folder Rules

- Do not create folders before they are needed.
- Do not add infrastructure folders just to look professional.
- Every folder should have a clear responsibility.
- Keep MVP code easy to navigate.

## Existing Static Demo

`taxdesk-command-center-demo.html` is a prototype, not the final app architecture.

Use it to understand screens and workflow. Do not treat it as production code.

