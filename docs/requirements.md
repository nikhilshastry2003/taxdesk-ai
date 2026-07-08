# TaxDesk Requirements

## Primary User

Nikhil's dad is the first user and design partner.

He manages recurring compliance work for clients, including:

- GSTR-3B.
- GSTR-1.
- EPF / ECR.
- ESI Challan / Claims.
- Saved challans, returns, acknowledgements, and related client documents.

## First Product Goal

Replace the Excel tick-mark checklist used to track pending compliance work.

## MVP Workflow

1. Dad opens TaxDesk.
2. Dashboard shows pending compliance counts for the selected period.
3. Dashboard shows only:
   - GSTR-3B.
   - GSTR-1.
   - EPF / ECR.
   - ESI Challan / Claims.
4. Dad clicks a pending item.
5. TaxDesk opens the matching Priority section, EPF page, ESI page, or Client page.
6. Dad sees the exact clients with pending work.
7. Dad opens a client and sees only that client's pending status for the selected period.
8. Dad uses Documents to search local saved files and folder links.

## MVP Pages

### Dashboard

Dashboard is the single source of truth for pending compliance.

It must show:

- GSTR-3B pending count.
- GSTR-1 pending count.
- EPF pending count.
- ESI pending count.
- Total pending count.
- Pending client list.

It must not show:

- Search bar.
- Assistant/chat.
- Waiting clarification.
- New task button.

### Priority

Priority mirrors Dashboard data exactly.

Requirements:

- Show sections for GSTR-3B, GSTR-1, EPF / ECR, and ESI Challan / Claims.
- Show Green / Completed when a section has zero pending clients.
- Show the same pending clients and tasks as Dashboard.
- Include search by client/task.
- Include period/year filtering.

### Client Page

Requirements:

- Show client identity and local folder path.
- Show selected client's pending compliance status.
- When opened from Dashboard/Priority, focus on pending status only.
- Link related documents if available.

### Documents

Requirements:

- Store links to local folders/files.
- Search by client name, file name, folder path, date, year, and financial year.
- Do not move files in MVP.

### EPF / ECR

Requirements:

- Show EPF pending clients.
- Show due date and proof status.
- Open client page from each row.

### ESI Challan / Claims

Requirements:

- Show ESI pending clients.
- Show due date and proof status.
- Open client page from each row.

## Explicitly Out Of Scope For MVP

- Assistant/chat.
- RAG.
- Embeddings.
- Agents.
- Clarification page.
- Monthly Work page.
- New task flow.
- SaaS auth/billing.
- GST portal scraping.
- OCR.
- Tally integration.

## Usefulness Test

The MVP is useful if:

- Dad can track monthly GSTR-3B, GSTR-1, EPF, and ESI work without Excel.
- Dashboard counts are correct.
- Priority exactly matches Dashboard.
- Client page makes pending work obvious.
- Documents page finds saved local files quickly.
