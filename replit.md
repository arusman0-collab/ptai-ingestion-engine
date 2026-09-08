# PT-AI Ingestion Engine

A portable, provenance-first scholarly ingestion and archival engine whose first collection is Rev. Stephen Tong material.

## Run & Operate

- `python -m ptai_ingestion --help` — inspect the portable ingestion CLI
- `python -m ptai_ingestion discover` — discover permitted local-drop candidates
- `python -m ptai_ingestion process [QUEUE_ID]` — process eligible candidates, or one numeric queue ID
- `uvicorn ptai_ingestion.api.app:app` — run the read-only operator API
- `python -m pytest -q` — run the Python Phase 1 test suite
- `pnpm --filter @workspace/ptai-ingestion-engine run dev` — run the operator dashboard
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- Optional env: `PTAI_CONFIG` and `PTAI_DATA_ROOT`; defaults remain under `./data`

## Stack

- Core: Python 3.11+, Typer, SQLite, PyYAML
- Operator API: FastAPI
- Extraction: BeautifulSoup and PyMuPDF
- Dashboard: React, Vite, TypeScript, Tailwind CSS

## Where things live

- `ptai_ingestion/` — portable ingestion engine and CLI
- `ptai_ingestion/migrations/` — additive SQLite schema migrations
- `tests/` — Phase 1 unit and integration tests
- `artifacts/ptai-ingestion-engine/` — Replit development/operator dashboard scaffolding (not portable core)
- `config.example.yml` — portable configuration example
- `README.md` — architecture, operation, safety, and Phase 1 limits

## Architecture decisions

- SQLite, the filesystem archive, processed text, metadata, and audit events are authoritative.
- The React dashboard is a development convenience; the CLI and Python engine must work without it.
- Originals are immutable. Derived metadata and text may be rebuilt without replacing originals.
- `needs_review` and `rights_hold` stop automated advancement.
- Qdrant and reasoning models belong to later phases and must remain replaceable.

## Product

- Discover local TXT, HTML, and PDF candidates from approved drop folders.
- Preserve eligible originals, compute SHA-256, extract text, and retain provenance.
- Allocate stable collection-aware Source IDs and record lifecycle events in SQLite.
- Inspect live API data through the operator dashboard without exposing archive files.

## User preferences

- Follow the attached PT-AI PRD and implement incrementally.
- Favor preservation, provenance, auditability, and offline portability over convenience.
- Never touch production `/ptai-data` during Replit development.

## Gotchas

- Phase 1 intentionally excludes Qdrant, Ollama, transcription, web discovery adapters, and production packaging.
- Replit development defaults to `./data`; production paths are configuration, never hard-coded.
- Existing Source IDs and catalog data must never be deleted, changed, or silently merged.

## Pointers

- The attached PRD is the product and architecture source of truth.
