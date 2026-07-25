# Design Note 002 - Client Management (v0.3)

Status: Draft, awaiting Nikhil's review. No implementation until approved.

Date: 2026-07-17

Roadmap milestone: v0.3, client management. First UI, first FastAPI code, first dependencies.

---

## Problem

Dad's clients exist only in his head and his folder tree. TaxDesk needs them as database rows before anything can be tracked. Typing 40 clients by hand into forms is exactly the kind of clerical pain this product promises to remove, so onboarding must come from the folders he already has.

## Why It Matters

Every later milestone reads these rows. Task generation in v0.4 walks client_services. The Dashboard counts tasks per client. The scanner in v0.6 walks each client's folder_path. This milestone also gives dad his first look at TaxDesk, and first impressions decide whether he keeps opening it.

## User Workflow

1. Dad opens TaxDesk in the browser on localhost.
2. First run, no root folder saved yet, so every page redirects to onboarding.
3. He pastes his client root path, for example `D:\Clients`, and submits.
4. TaxDesk lists the subfolders as client candidates, each with a ticked checkbox.
5. He unticks the folders that are not clients, like `Backup` or `Old`, and confirms.
6. Each ticked folder becomes a client with its folder path saved.
7. He opens any client and ticks which of the 4 services apply.
8. From then on, the client list is his registry, and onboarding can be rerun safely to pick up new folders.

## Data Involved

- settings: the `root_folder` row, written once at onboarding
- clients: one insert per confirmed folder, name from the folder name
- client_services: ticked service inserts a row, unticked sets active to 0

## Pages And Routes

```text
GET  /                      redirect to /clients, or /onboarding when no root folder yet
GET  /onboarding            form asking for the root folder path
POST /onboarding/root       save the path, show discovered subfolders
POST /onboarding/confirm    create clients from the ticked folders
GET  /clients               client list
GET  /clients/{id}          client detail, folder path, service checkboxes
POST /clients/{id}/services save service ticks
```

Every POST ends in a redirect to a GET page. This is the post redirect get pattern, and it exists so a browser refresh can never resubmit a form.

## New Dependencies, The First In The Project

Per the engineering guide, each one justified.

1. **fastapi.** Routing, request parsing, form handling. The alternative is the standard library's http.server, which means hand writing routing, form decoding, and error handling, roughly its own project. FastAPI is the mainstream Python choice with a huge community and it matches ADR 001.
2. **uvicorn.** FastAPI is only the application layer, it cannot listen on a port. Uvicorn is the server that runs it. They are the standard pairing.
3. **jinja2.** HTML pages with variables and loops. The alternative is building HTML by string concatenation, which is unreadable and unsafe. Jinja2 escapes values automatically, which closes the script injection hole by default.

All three get pinned versions in a new pyproject.toml. Nothing else comes in.

## Files

```text
pyproject.toml              new, project metadata plus the 3 pinned dependencies
app/main.py                 FastAPI app, runs migrations at startup, includes routes
app/routes/clients.py       list, detail, service saving
app/routes/onboarding.py    root form, discovery, confirm
app/db/queries.py           typed SQL functions, the only file where app SQL lives
app/templates/base.html     shared page frame
app/templates/onboarding.html
app/templates/clients.html
app/templates/client_detail.html
```

## Design Decisions

- Pages rendered on the server with Jinja2, no JavaScript framework, per ADR 001.
- migrate() runs inside app startup, so dad never types a command. Installing and opening the app is enough.
- Discovery proposes, never creates. Dad confirms the list. Same confirm first principle the scanner will use later.
- Unticking a service sets active to 0 instead of deleting the row. Deactivation is not deletion, decided in design note 001.
- All SQL lives in app/db/queries.py as small typed functions. Routes call functions, never write SQL. One clean boundary between web code and database code.

## Edge Cases

- Root path does not exist or is a file. Show the error on the form, save nothing.
- Root folder is empty. Say so plainly, save the setting anyway.
- Onboarding rerun with the same root. Existing names are skipped by INSERT OR IGNORE on the unique client name, so no duplicates, and newly ticked folders just get added.
- A client folder renamed after onboarding leaves a dangling folder_path. The v0.6 scan reports it, out of scope here.
- Visiting any page before onboarding redirects to onboarding instead of showing empty screens.

## Testing Plan, Manual

1. Fresh scratch database, start the app, visit /clients, expect a redirect to onboarding.
2. Point it at a scratch folder containing 3 subfolders, expect 3 candidates.
3. Untick one, confirm, expect 2 clients in the list.
4. Open a client, tick GSTR_3B and EPF, save, reopen, expect both still ticked.
5. Untick EPF, save, then query client_services directly, expect the row still there with active 0.
6. Rerun onboarding with the same root, expect zero duplicate clients.
7. Run seed first, then expect the 6 seed clients in the list alongside.

Automated tests arrive in v0.4 with the task generation logic, as decided earlier.

## Risks

- Dad's machine is Windows, development is on Linux. pathlib everywhere, and the real path handling gets proven on his machine in v0.7.
- A browser cannot open a folder picker for the server's disk, so dad pastes the path as text. Acceptable for MVP, revisit at packaging time.

## Non Goals

Dashboard, Priority, task generation, documents, the scanner, and visual polish. Plain readable pages only.

## Concepts To Explain At Implementation

FastAPI and what ASGI means, uvicorn's role, routing, Jinja2 templates and automatic escaping, the post redirect get pattern, and the layering rule of routes versus queries.
