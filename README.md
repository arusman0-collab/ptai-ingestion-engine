# PT-AI Ingestion Engine — Phase 1

Portable Python 3.11+ foundation for a provenance-first scholarly archive. Phase 1 ingests local `.txt`, `.html`, and embedded-text `.pdf` files only; it does not contact Qdrant, Ollama, external sites, or production services.

## Setup
`cp config.example.yml config.yml`, install with `pip install -e '.[test]'`, then place permitted files in `./data/drop`.

```sh
ptai-ingest discover
ptai-ingest queue
ptai-ingest process
ptai-ingest status --json
ptai-ingest verify-integrity
uvicorn ptai_ingestion.api.app:app
pytest
```

`process` processes all new candidates. `process QUEUE_ID` targets the numeric queue ID shown by `ptai-ingest queue`; an unknown or non-new ID is an explicit error, never a silent no-op. Source IDs are allocated only when eligible processing begins and are permanent. The API exposes `/api/status`, `/api/sources`, `/api/sources/{source_id}`, `/api/queue`, and `/api/review`; it never serves originals or processed copyrighted files.

## Archive and integrity

All runtime data is beneath configurable `data_root` (development default `./data`): `original/`, `processed/`, `metadata/`, `catalog/`, and `drop/`. Original files are copied before extraction to a SHA-prefix named immutable location. Extracted-text provenance is persisted in a sidecar metadata JSON file. Existing content is compared by SHA-256 and never overwritten. `verify-integrity` reports `OK`, `missing`, `hash mismatch`, or `unreadable`; it never repairs content.

SQLite migrations are in `ptai_ingestion/migrations`, tracked in `schema_migrations`, and are additive. The schema includes collection-aware permanent source allocation, works/manifestations, queue, rights, events, and scholarly relation tables. Every lifecycle operation writes `processing_events`. `needs_review` and `rights_hold` block automated advancement. Unknown/restricted rights are held before acquisition.

## Phase 1 limitations

OCR, media transcription, web adapters, semantic deduplication, chunking, embedding, Qdrant, retrieval, scheduler, Docker packaging, and a mutating review interface are deliberately later phases. PDFs without embedded text fail extraction and remain inspectable. Exact SHA duplicates are flagged `duplicate`, never silently merged.

## Backup

Back up the entire configured data root, particularly `catalog/ptai_catalog.db`, `original/`, `processed/`, and configuration. Restore by stopping writers and restoring those paths together. Future vector indexes are rebuildable and are not authoritative.