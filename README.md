# TaxDesk, What We Are Building

TaxDesk is a local first compliance command center for a solo Indian
tax practitioner. The first user is dad. It replaces the Excel tick
sheet he uses to track which client still owes which monthly filing,
and where the proof file for each finished one lives.

This repo is being rebuilt from scratch by Nikhil, by hand, to learn.
The finished reference implementation is preserved in git tags, see
the bottom.

## The problem

Dad manages four recurring filings for his clients, GSTR-3B, GSTR-1,
EPF, ESI. He tracks them with hand ticks in Excel. Ticks get
forgotten, the sheet drifts from reality, and a missed filing means a
government penalty with a client's name on it. Proof files, challans
and acknowledgements, sit in client folders with no link to the ticks.

## The one question the product must answer

Which clients have pending GSTR-3B, GSTR-1, EPF, or ESI work this
month, and where is the proof for the finished ones.

## What it must do

1. Onboard clients from dad's existing folder tree. He points the app
   at his root folder once, each subfolder becomes a client candidate,
   he confirms with checkboxes. Nothing auto creates.
2. Track which of the four services each client needs. Switching a
   service off must never delete history.
3. Each month, generate one pending task per client per active
   service. Generating twice must never create duplicates, the
   database itself should make that impossible.
4. Let dad mark tasks done or not applicable, recording when and how
   a task was completed. A finished month can be closed, and a closed
   month refuses changes.
5. Show a Dashboard, pending counts per service plus the list of
   clients with pending work, for a chosen month. Show a Priority
   page listing the same tasks grouped by service, searchable by
   client name. The two pages must never be able to disagree, which
   means both must read the same source, computed fresh, never stored
   counts.
6. Later, a Documents page searching saved file links, and a scanner
   that reads filenames in client folders, detects proof files, and
   suggests them for one click confirmation. Nothing marks itself
   done silently.

## What it must not be

- no cloud, no accounts, dad's data never leaves his machine
- no AI in version one
- no authentication in version one, it runs on localhost for one user
- not a Tally replacement, not a government portal automation

## Decided stack

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

## The answer key

The complete previous implementation, with its tests, journal, and
teaching documents, is preserved in two tags.

```bash
git show v0.5-reference -- .                    # browse the finished product
git show docs-reference:docs/deep-dive.md       # read a teaching doc
git checkout v0.5-reference -- tests/           # restore the test suite as a target
```

The rebuild rule. Think first, struggle a little, then peek, then ask.
