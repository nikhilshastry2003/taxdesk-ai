# Design Note 004 - Dashboard And Priority (v0.5)

Status: Draft, awaiting Nikhil's review. No implementation until approved.

Date: 2026-07-26

Roadmap milestone: v0.5, Dashboard becomes the source of truth.

---

## Problem

The tracker works but answers slowly. Pending work hides inside a period page table. Dad's morning question is a glance question, what is pending, how much, for which clients. There is no page that answers it in five seconds yet.

## Why It Matters

The vision doc's north star is exactly this glance. Dashboard is the page dad opens instead of Excel, and the requirements call it the single source of truth. If this page is right, the product feels done to him. Everything before it was plumbing.

## User Workflow

1. Dad opens TaxDesk. He lands on the Dashboard.
2. It shows the latest open month by default, a dropdown switches months.
3. Four cards, one per service, each with its pending count, plus a total and the list of clients that still have pending work.
4. He clicks the GSTR-3B card. Priority opens, filtered to GSTR-3B, the exact same clients the number promised.
5. On Priority he searches a client by name, sees each section, and any service with nothing pending shows Green, completed.
6. He clicks a client name anywhere. The client page opens showing that client's pending tasks for the month.
7. Marking done still happens where tasks live, one click away, and the Dashboard numbers shrink on the next glance.

## Data Involved

No new tables, no new columns, no migration. Both pages read `compliance_tasks` joined to `clients`, filtered by period. Counts are computed by GROUP BY at read time, never stored, which is the structural reason Dashboard and Priority cannot disagree.

## Pages And Routes

```text
GET /dashboard                 counts per service, total, pending client list, period dropdown
GET /priority                  all four service sections for the period
GET /priority?service=EPF      the same page filtered to one service, this IS the EPF / ECR view
GET /clients/{id}?period={id}  client detail gains a pending tasks section for that period
GET /                          now redirects to /dashboard (onboarding still wins when no root folder)
```

All GET, this milestone writes nothing. The two dedicated pages the architecture doc wanted for EPF and ESI are Priority filtered by service, one template, four views, nothing extra to maintain.

## Design Decisions

- **Dashboard stays clean by rule.** No search box, no new-task button, no actions, per the requirements. Numbers, names, links only.
- **Default period is the newest open one.** No open periods, newest of any status. No periods at all, the page says so and links to Periods.
- **The mirror guarantee is enforced by construction and by test.** Both pages call the same query functions with the same filters. One pytest test computes Dashboard counts and counts Priority rows per service and asserts they are equal, so the requirement "Priority exactly mirrors Dashboard" is machine checked, not promised.
- **Green, completed.** A service section with zero pending shows a green completed line instead of an empty table, per the requirements.
- **Search is server side and simple.** A text input on Priority filters client names with SQL LIKE. No JavaScript.
- **Client pending view via query parameter.** The existing client detail template gains a pending section when a period is in context. No separate page.

## Files

```text
app/routes/dashboard.py          dashboard and priority routes
app/db/queries.py                pending_counts, pending_tasks, period pick helpers
app/routes/clients.py            small addition, pending tasks on client detail
app/templates/dashboard.html
app/templates/priority.html
app/templates/client_detail.html small addition
app/templates/base.html          nav gains Dashboard and Priority
app/routes/clients.py            home redirect now targets /dashboard
tests/test_dashboard.py          counts, mirror guarantee, search, defaults
```

## Edge Cases

- No periods exist yet, Dashboard says so plainly and links to Periods, no crash, no blank page.
- A period with zero generated tasks shows all four cards at zero with a hint to generate.
- All tasks done, total pending is zero, every Priority section is green, the happiest possible screen.
- Search text matching nothing shows an honest empty result, not an error.
- A service query value that is not one of the four is ignored and the full Priority shows.
- not_applicable tasks are neither pending nor shown as green weight, they simply do not count, matching how dad thinks about them.

## Testing Plan

pytest on temp databases, as established.

1. Pending counts per service match hand computed expectations from a known fixture.
2. Mirror guarantee, per service, Dashboard count equals the number of Priority rows.
3. done and not_applicable tasks vanish from counts and lists.
4. Search filters by name fragment, case insensitive.
5. Default period selection picks the newest open period.
6. Client pending view lists only that client's pending tasks for the period.

Plus the manual click-through, seed data, glance the Dashboard, drill into Priority, search, open a client, mark something done on the period page, watch the numbers shrink.

## Risks

- Two pages reading identical queries can drift if someone later adds a filter to one and not the other. Mitigated by sharing the exact query functions and by the mirror test, which fails loudly on drift.

## Non Goals

Documents, the scanner, due date urgency colors, charts, styling polish, closing the loop on proofs. Also no marking done FROM the Dashboard, it stays read only by rule.

## Concepts To Explain At Implementation

Query parameters as page filters, SQL LIKE and case sensitivity, computing versus storing aggregates one more time in practice, and how a test can enforce a product requirement, the mirror guarantee, forever.
