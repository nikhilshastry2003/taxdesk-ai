# TaxDesk Roadmap

## Version 0.1 - Documentation And Decisions

Goal:

Create the repo foundation and agree on the product boundary.

Deliverables:

- README.
- Vision.
- Requirements.
- Architecture.
- Tech stack.
- Folder structure.
- Engineering journal.

No app code.

## Version 0.2 - Domain And Database Design

Goal:

Design the data model before building UI.

Deliverables:

- Client model.
- Client service model.
- Compliance period model.
- Compliance task model.
- Document model.
- Seed data for 5-10 sample clients.

Success:

Nikhil can explain the database schema without looking at generated code.

## Version 0.3 - Client Management

Goal:

Add and view clients.

Deliverables:

- Client list.
- Client detail.
- Local folder path field.
- Active service configuration.

Success:

Dad's first 10 clients can be entered accurately.

## Version 0.4 - Compliance Task Generation

Goal:

Generate monthly pending tasks from active client services.

Deliverables:

- Period selector.
- Generate tasks for GSTR-3B, GSTR-1, EPF, ESI.
- Mark pending/done/not applicable.

Success:

TaxDesk can represent dad's Excel checklist for one month.

## Version 0.5 - Dashboard And Priority

Goal:

Dashboard becomes the source of truth.

Deliverables:

- Pending compliance cards.
- Pending client list.
- Priority page synced with Dashboard.
- Priority search.

Success:

Dashboard and Priority show the same pending clients.

## Version 0.6 - Documents

Goal:

Link and search local client files.

Deliverables:

- Document records.
- Folder/file path storage.
- Search by client, file, year, financial year.

Success:

Dad can find common saved files faster than using Windows Explorer.

## Version 0.7 - Real Dad Trial

Goal:

Use TaxDesk for one real monthly cycle.

Success:

Dad opens TaxDesk instead of Excel for compliance tracking.

## Later - AI And Retrieval

Only after real usage:

- File indexing.
- Document text extraction.
- Better document search.
- RAG with citations.
- Tool-calling assistant.

AI should solve observed problems, not imagined ones.
