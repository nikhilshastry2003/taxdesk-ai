# TaxDesk Architecture

## Architecture Principle

Keep version 1 boring, local, and understandable.

TaxDesk should be simple enough for Nikhil to explain every module without hiding behind framework magic.

## High-Level Shape

```text
UI
 |
Application logic
 |
Domain functions
 |
SQLite persistence
 |
Local client folders
```

## Local-First MVP

TaxDesk runs on the practitioner's computer.

Core data is local:

- Clients.
- Active compliance services.
- Compliance periods.
- Pending/done compliance tasks.
- Document links.

Local files remain where they already are. TaxDesk stores paths and metadata; it does not restructure folders in MVP.

## Main Domain Concepts

### Client

A party/business/person whose compliance work is tracked.

Important fields:

- Name.
- Local folder path.
- Phone/email if useful.
- Notes.

### Client Service

Which compliance services apply to a client.

Allowed MVP services:

- GSTR-3B.
- GSTR-1.
- EPF.
- ESI.

### Compliance Period

The selected month/year or financial year being tracked.

### Compliance Task

A pending or completed compliance item for one client in one period.

Examples:

- ABC Traders -> GSTR-3B -> July 2026 -> Pending.
- Kumar Textiles -> EPF / ECR -> July 2026 -> Done.

### Document

A local file or folder link associated with a client, period, or compliance item.

## First Data Model Draft

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
task_label
status            # pending, done, not_applicable
due_date
proof_status      # missing, linked, not_required
proof_file_path
completed_at
notes
```

### documents

```text
id
client_id
period_id
document_type
file_path
filename
document_date
year
financial_year
notes
created_at
```

## MVP Screens

- Dashboard.
- Priority.
- Clients.
- Client detail.
- Documents.
- EPF / ECR.
- ESI Challan / Claims.

## Out Of Scope Architecture

Do not add these in version 1:

- Multi-agent orchestration.
- Plugin system.
- Event bus.
- CQRS.
- Microservices.
- Cloud database.
- Auth/billing.
- RAG pipeline.

## Later AI Architecture

AI can be added after the tracker and document search are useful.

Possible later layers:

```text
Local file index
 |
Keyword search
 |
Document parsing
 |
Embeddings
 |
RAG with citations
 |
Tool-calling assistant
```

RAG should answer only from retrieved source files and must cite the local document used.
