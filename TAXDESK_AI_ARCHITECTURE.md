# TaxDesk AI - Compliance Command Architecture

> Current direction as of July 4, 2026.
> TaxDesk is a local-first compliance command center for tax practitioners.
> Dashboard is the single source of truth for pending work.

---

## Product Thesis

TaxDesk helps a tax practitioner see and act on pending compliance work for each client without maintaining a separate Excel tick-mark sheet.

The MVP focuses only on the compliance items dad actually wants to track first:

- GSTR-3B
- GSTR-1
- EPF / ECR
- ESI Challan / Claims

Tally remains the accounting system. Government portals remain the filing systems. TaxDesk is the local command layer that shows what is pending, which client it belongs to, and where the saved proof/documents are.

---

## MVP Rules

### Keep

- Dashboard
- Priority page
- Client page
- Documents page
- Pending compliance items:
  - GSTR-3B
  - GSTR-1
  - EPF
  - ESI

### Remove Or Disable For Now

- Waiting clarification section
- Clarification page
- Monthly Work page
- New Task button
- Dashboard search bar
- Assistant/chat page

Reason: dad wants the Dashboard and Client pages to provide the required information directly. We should not add extra pages until there is a clear workflow input for them.

---

## Dashboard

The Dashboard is the single source of truth for pending compliance.

It should show only pending compliance items:

```text
GSTR-3B pending: 2 clients
GSTR-1 pending: 1 client
EPF & ESI:
  EPF pending: 2 clients
  ESI pending: 1 client
Total pending: 6 items
```

Dashboard should not include:

- Search bar
- Waiting clarification
- New task action
- Assistant shortcuts

Click behavior:

- Clicking GSTR-3B opens Priority filtered to GSTR-3B.
- Clicking GSTR-1 opens Priority filtered to GSTR-1.
- Clicking EPF opens EPF / ECR page.
- Clicking ESI opens ESI Challan / Claims page.
- Clicking a pending client row opens that client's page with only that client's pending status.

---

## Priority Page

Priority must exactly mirror Dashboard pending data.

Rules:

- If Dashboard shows 0 pending for a compliance item, that section is Green / Completed.
- If Dashboard shows pending work, Priority shows the exact same client/task list.
- Party-wise/client-wise list must match Dashboard data.
- Priority includes search to quickly find a client.
- Priority supports filtering by dates, months, and financial years.

Priority sections:

```text
GSTR-3B
GSTR-1
EPF / ECR
ESI Challan / Claims
```

---

## Client Page

Client page remains useful and should be kept.

When opened normally, it can show client service setup and documents.

When opened from Dashboard or Priority, it should focus on only that client's pending compliance status for the selected period.

Example:

```text
Client: ABC Traders
Period: July 2026

Pending:
- GSTR-3B due 20 July 2026
- EPF / ECR due 15 July 2026

Documents:
- Local folder path
- Saved challans / acknowledgements if linked
```

---

## Documents Page

Documents page stays because local files and folders matter.

Requirements:

- Link to local client folders.
- Search by client name.
- Search by document name.
- Search by local folder path.
- Filter/search by date, year, or financial year.

Documents should not move files in MVP. They should only store and open local paths.

---

## EPF / ECR Page

EPF should open a dedicated EPF / ECR section.

It should show:

- EPF pending clients.
- Due date.
- ECR/proof status.
- Link back to client page.

EPF and ESI should remain separate after opening.

---

## ESI Challan / Claims Page

ESI should open a dedicated ESI Challan / Claims section.

It should show:

- ESI pending clients.
- Due date.
- Challan/claims proof status.
- Link back to client page.

---

## Search Behavior

Dashboard does not have search.

Search lives in:

- Priority page for pending compliance/client search.
- Client page for client search.
- Documents page for local folder/document search.

Client search behavior:

- Searching for a client opens the Client page.
- The Client page directly displays that client's pending status.

Document search behavior:

- Search local document folder records.
- Support client name, file name, path, year, and financial-year filters.

---

## Data Model

### clients

```text
id
name
folder_path
phone
email
notes
created_at
updated_at
```

### client_services

```text
id
client_id
service_type      # GSTR_3B, GSTR_1, EPF, ESI
active
notes
```

### compliance_periods

```text
id
month
year
financial_year
status            # open, closed
```

### compliance_tasks

```text
id
client_id
period_id
service_type      # GSTR_3B, GSTR_1, EPF, ESI
status            # pending, done, not_applicable
due_date
proof_status      # missing, detected, linked, not_required
proof_file_path
completed_at
completed_source  # manual, scan_confirmed
notes
```

### documents

```text
id
client_id
period_id
document_type     # gstr_3b, gstr_1, epf_ecr, esi_challan, itr_ack, other
file_path
filename
document_date
year
financial_year
notes
created_at
```

### settings

```text
key               # e.g. root_folder
value
```

---

## Build Order

1. Dashboard pending compliance cards.
2. Priority page synced from Dashboard data.
3. Client page pending-status view.
4. EPF / ECR detail page.
5. ESI Challan / Claims detail page.
6. Documents page with local search.
7. Date/year/financial-year filters.
8. Later: file indexing and document retrieval.
9. Later: AI/chat only if a specific workflow proves useful.

---

## MVP Success Criteria

The MVP succeeds if dad can stop using his Excel checklist for these items:

- GSTR-3B
- GSTR-1
- EPF
- ESI

Gate tests:

1. Add 10 real clients.
2. Configure which clients need GSTR-3B, GSTR-1, EPF, and ESI.
3. Generate pending tasks for the selected month.
4. Dashboard shows correct pending counts.
5. Priority page exactly matches Dashboard counts and clients.
6. Clicking a pending item opens the correct client pending view.
7. EPF opens EPF / ECR page.
8. ESI opens ESI Challan / Claims page.
9. Documents page finds local client documents by name, year, and path.
10. Dad says the Dashboard is easier than the Excel tick sheet.

---

## One-Line North Star

TaxDesk should answer this immediately:

```text
Which clients have pending GSTR-3B, GSTR-1, EPF, or ESI work, and where is the related proof/document?
```
