# Design Note 003 - Compliance Task Generation (v0.4)

Status: Draft, awaiting Nikhil's review. No implementation until approved.

Date: 2026-07-26

Roadmap milestone: v0.4, compliance task generation. This is the milestone that functionally replaces the Excel tick sheet.

---

## Problem

Clients and their services now live in the database, but months do not. Dad needs to pick a month, get one pending task per client per active service, and mark each one done as he files. Until this exists, TaxDesk holds a client registry and nothing to track.

## Why It Matters

The roadmap's own success line for v0.4 reads, TaxDesk can represent dad's Excel checklist for one month. Every page after this, Dashboard, Priority, EPF, ESI, only displays what this milestone creates.

## User Workflow

1. Dad opens the new Periods page.
2. He picks month and year, say July 2026, and creates the period. The financial year is computed for him.
3. He clicks generate. One pending task appears for every client with an active service, thirteen clients strong or three, the same click.
4. He opens the period and sees tasks grouped by service, each with its client name and status.
5. As he files during the month, he marks tasks done. A wrong entry can go back to pending, and a task that does not apply this month becomes not applicable.
6. Generate can be clicked again any time, existing tasks are untouched, only missing ones appear, for example after adding a new client mid month.
7. When the month is finished he can close the period, which freezes it against accidental changes. Reopen exists too.

## Data Involved

- compliance_periods: created from the form, unique per month and year
- compliance_tasks: generated rows, status updates
- client_services: the source generation reads, active rows only

## Pages And Routes

```text
GET  /periods                    list periods, form to create one
POST /periods                    create period, computed financial year
GET  /periods/{id}               tasks of the period, grouped by service
POST /periods/{id}/generate      create missing tasks for the period
POST /periods/{id}/toggle-close  close an open period, reopen a closed one
POST /tasks/{task_id}/status     set pending, done, or not_applicable
```

Same rules as v0.3, every POST redirects to a GET page.

## Design Decisions

- **Financial year is computed, never typed.** India's financial year runs April to March. Month 4 or later belongs to `year to year+1`, month 1 to 3 belongs to `year-1 to year`. Derived data stays out of forms, same principle as pending counts.
- **Due dates ship as a placeholder.** A single `DUE_DAY_RULES` mapping in code holds the due day of month per service, every entry None until dad confirms the real days. Generation fills due_date only where a rule exists, otherwise NULL. Filling in dad's answers later is a one line edit per service and a regenerate is not even needed, a small backfill can set dates on existing tasks then.
- **Generation is the proven idempotent INSERT.** The same INSERT OR IGNORE SELECT the seed already exercises, the UNIQUE constraint does the duplicate protection.
- **Closed periods refuse writes.** Generation and status changes against a closed period return an error message instead of writing. The rule comes from design note 001, this milestone enforces it in the routes.
- **Marking done records how.** Done sets completed_at and completed_source manual. Moving back to pending clears both. The scanner will use scan_confirmed for its own confirmations in v0.6.
- **First automated tests arrive.** pytest was scheduled for exactly this milestone, because generation and status rules are the first logic worth locking down. Tests run against throwaway databases in a temp folder, never the real one.

## New Dependency, Development Only

**pytest**, pinned, in a dev dependency group, not shipped with the app. Justification per the guide, generation correctness, duplicate protection, status transitions, and financial year math are exactly the logic the guide says must eventually have automated tests, and this is the milestone that creates that logic. The alternative, assert scripts run by hand, rebuilds pytest badly.

## Files

```text
app/routes/periods.py            period list, create, generate, close, task status
app/services/generation.py       generation and financial year logic, pure functions, no HTTP
app/db/queries.py                new functions for periods and tasks
app/templates/periods.html
app/templates/period_detail.html
tests/conftest.py                scratch database fixture
tests/test_generation.py         generation, idempotency, financial year
tests/test_task_status.py        status transitions, closed period refusals
pyproject.toml                   pytest in a dev group
```

app/services/ appears now because generation logic deserves a home routes can call and tests can import without any web machinery. This is the services layer the folder structure draft always planned.

## Edge Cases

- Generate with zero clients or zero active services, zero tasks, the page says so plainly.
- Generate twice, second run inserts nothing, proven by count.
- A service deactivated after generation, its existing task stays, regeneration does not resurrect anything extra.
- A client added mid month, regenerate creates only that client's tasks.
- Creating a period that already exists, INSERT OR IGNORE keeps the original, the form lands on the existing one.
- Status value outside the allowed three, rejected by the CHECK constraint, surfaced as an error.
- Any write against a closed period, refused with a visible message.
- Month 13 or year 1900, rejected by the CHECK constraints on the table.

## Testing Plan

pytest, each test on a fresh temp database with migrations applied by the fixture.

1. Generation creates exactly one task per client per active service.
2. Second generation run creates zero new rows.
3. Deactivated service generates nothing, existing task survives.
4. Financial year computation, month 4 gives `2026-27`, month 3 gives `2025-26`, month 1 and month 12 boundaries included.
5. Done sets completed_at and completed_source, back to pending clears them.
6. Writes against a closed period are refused.

Plus a manual click through of the workflow above with seed data.

## Risks

- Due dates displayed as empty until dad's rules land, dad might read empty as broken. The period page will show a quiet placeholder instead of blank.
- Task list length, 40 clients times 4 services is 160 rows on one page. Fine for MVP, grouping by service keeps it scannable, no pagination yet.

## Non Goals

Dashboard and Priority pages, due date urgency colors, the scanner, proof linking UI, notifications. Also no automatic period creation on month change yet, that convenience idea waits until dad actually forgets to create one.

## Concepts To Explain At Implementation

pytest and fixtures, temp databases in tests, the services layer versus routes, pure functions and why testable logic avoids HTTP, and India's financial year computation.
