# TaxDesk

A local first compliance command center for a solo Indian tax
practitioner. It replaces the Excel tick sheet used to track which
client still owes which monthly filing, and remembers where the proof
file for every finished one lives. The first user is dad, the first
machine is his office computer, and his data never leaves it.

This repo is being rebuilt from scratch by Nikhil, by hand, to learn.
The finished reference implementation is preserved in the git tags
`v0.5-reference` and `docs-reference`.

## The problem

Dad manages four recurring filings for his clients, GSTR-3B, GSTR-1,
EPF, ESI. He tracks them with hand ticks in Excel. Ticks get
forgotten, the sheet drifts from reality, and a missed filing means a
government penalty with a client's name on it. Proof files, challans
and acknowledgements, sit in client folders with no link to the ticks.

The one question the product must answer every morning. Which clients
have pending GSTR-3B, GSTR-1, EPF, or ESI work this month, and where
is the proof for the finished ones.

## The architecture

A small web app running on localhost, one process, one database file.
Three layers, and each layer talks only to the one below it.

```text
browser (dad clicks)
   |            HTTP requests and responses
web layer       routes, one function per page, parses input, redirects
   |            plain function calls
logic layer     the business rules and every SQL statement, in one place
   |            SQL over a single connection per request
SQLite          taxdesk.db, one local file, enforces the data rules itself
   |
disk            dad's existing client folders, read, never restructured
```

Why this shape. Pages must never contain business rules, rules must
never contain SQL scattered around, and the hard guarantees, like no
duplicate task ever, live in the database itself where no code bug can
break them.

What the database holds, at the concept level.

- clients: who dad works for, each linked to its folder on disk
- client services: which of the four filings each client needs
- periods: one row per tracked month
- tasks: the heart, one row per client per service per month, with
  status and proof
- documents: saved file links for search, later milestone
- settings: small app facts, like the root folder path

Two structural promises the design keeps. The Dashboard and the
Priority list read the same source with the same filters, so they can
never disagree. And every repeatable action, generating a month,
rerunning setup, is idempotent, meaning running it twice changes
nothing more than running it once.

## What it must do

1. Onboard clients from dad's existing folder tree. He points the app
   at his root folder once, each subfolder becomes a client candidate,
   he confirms with checkboxes. Nothing auto creates.
2. Track which of the four services each client needs. Switching a
   service off must never delete history.
3. Each month, generate one pending task per client per active
   service. Generating twice must never create duplicates.
4. Let dad mark tasks done or not applicable, recording when and how.
   A finished month can be closed, and a closed month refuses changes.
5. Show a Dashboard with pending counts per service and the clients
   that still owe work, and a Priority page listing the same tasks
   grouped by service, searchable by client name.
6. Later, a Documents page searching saved file links, and a scanner
   that reads filenames in client folders, detects proof files, and
   suggests them for one click confirmation. Nothing marks itself
   done silently.

## What it must not be

- no cloud, no accounts, dad's data never leaves his machine
- no AI in version one
- no authentication in version one, it runs on localhost for one user
- not a Tally replacement, not a government portal automation

## Stack

Python, FastAPI, SQLite, Jinja2 templates, raw SQL with no ORM,
pytest for tests. Chosen for transparency, every layer must be
explainable by its builder.

## Build order

1. Database schema and a migration runner
2. Seed data for development
3. Client onboarding and service configuration pages
4. Periods, task generation, statuses, month closing
5. Dashboard and Priority
6. Documents and the proof scanner
7. Real trial on dad's machine

## Definition of done

Dad opens TaxDesk instead of Excel for one real month, the counts are
right, and finding a proof file is faster than Windows Explorer.
