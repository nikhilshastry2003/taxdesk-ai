# TaxDesk Tech Stack

## Current Decision

The MVP should be local-first and simple.

Recommended stack for the real app:

- Next.js.
- React.
- TypeScript.
- TailwindCSS.
- shadcn/ui.
- Prisma.
- SQLite.

## Why This Stack

### Next.js + React + TypeScript

Good for building a local browser-based app quickly while keeping UI code structured and typed.

### TailwindCSS + shadcn/ui

Fast UI development with consistent components.

### Prisma + SQLite

SQLite is enough for one local office.

Prisma gives a readable schema and type-safe database access.

### Local Browser App First

Start with a localhost app before packaging.

This avoids installer complexity while dad tests the workflow.

### Tauri Later

If the local browser app proves useful, package it as a desktop app with Tauri.

## What Not To Add Yet

- Supabase.
- Clerk.
- Stripe.
- Cloud Postgres.
- Docker.
- Kubernetes.
- Background job systems.
- Vector database.
- AI SDKs.

## Existing Repo Note

The older Python file-indexer direction was removed from the repo in July 2026.

The stack decision above is still the open choice to confirm before app code is written.

Do not mix stacks accidentally.

## AI Later

When AI becomes justified by usage, possible stack additions:

- File indexing module.
- PDF/text parser.
- Embedding provider.
- Local vector store or SQLite-based retrieval.
- RAG answer generation with citations.
- Tool-calling assistant over structured compliance data.
