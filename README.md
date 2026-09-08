# PT-AI Ingestion Engine — Phase 2

Portable Python 3.11+ provenance-first archive. Phase 2 retains Phase 1 local ingestion and adds deterministic retrieval indexing; it contains no crawler, OCR enhancement, transcription, or reasoning/chatbot model.

## Setup
`cp config.example.yml config.yml`, install with `pip install -e '.[test]'`, then place permitted files in `./data/drop`.

```sh
ptai-ingest discover
ptai-ingest queue
ptai-ingest process
ptai-ingest reindex ST-000001
ptai-ingest rebuild-index
ptai-ingest status --json
ptai-ingest verify-integrity
uvicorn ptai_ingestion.api.app:app
pytest
```

`process` processes all new candidates. `process QUEUE_ID` targets the numeric queue ID shown by `ptai-ingest queue`; an unknown or non-new ID is an explicit error, never a silent no-op. Source IDs are allocated only when eligible processing begins and are permanent. The API exposes `/api/status`, `/api/sources`, `/api/sources/{source_id}`, `/api/queue`, and `/api/review`; it never serves originals or processed copyrighted files.

## Archive and integrity

All runtime data is beneath configurable `data_root` (development default `./data`): `original/`, `processed/`, `metadata/`, `catalog/`, and `drop/`. Original files are copied before extraction to a SHA-prefix named immutable location. Extracted-text provenance is persisted in a sidecar metadata JSON file. Existing content is compared by SHA-256 and never overwritten. `verify-integrity` reports `OK`, `missing`, `hash mismatch`, or `unreadable`; it never repairs content.

SQLite migrations are in `ptai_ingestion/migrations`, tracked in `schema_migrations`, and are additive. The schema includes collection-aware permanent source allocation, works/manifestations, queue, rights, events, and scholarly relation tables. Every lifecycle operation writes `processing_events`. `needs_review` and `rights_hold` block automated advancement. Unknown/restricted rights are held before acquisition.

## Vector indexing and retrieval

Run Qdrant at the configured `qdrant.url` (default `http://localhost:6333`) and pull the configured Ollama model:
```sh
ollama pull nomic-embed-text
```
`reindex SOURCE_ID` replaces only that source's vectors. `rebuild-index` prepares every source first, builds a verified staging collection, and atomically switches the configured Qdrant alias only after the staged point count is complete. A failed rebuild leaves the active alias unchanged. Qdrant is intentionally non-authoritative and can always be deleted and rebuilt from SQLite and processed archival text. The configured `qdrant.collection` must be a logical alias; a legacy physical collection using that exact name must be explicitly removed or migrated before rebuilding.

Chunking is deterministic and paragraph-first using `max_chars`, `min_chars`, and `overlap_chars`; preserved PDF page markers and section headings are carried into evidence metadata. Index metadata records chunking version, embedding model/version, and dimensions. Ollama document inputs use `search_document: ` and queries use `search_query: `.

`POST /api/search` accepts `{"query":"...", "limit":8, "collection":"stephen-tong"}` and returns scored evidence/provenance only, never an AI-generated answer. Failures leave preserved originals and catalog records intact and are recorded as `indexing_failed`; retry with `reindex`.

Troubleshooting: ensure Qdrant is reachable and `ollama pull nomic-embed-text` completed. If an index is corrupt or lost, remove the active alias/physical vector collections as appropriate, then run `ptai-ingest rebuild-index`; never delete the archive data root. Staging collections left by an interrupted process can be removed after confirming they are not the active alias target.

## Limitations

OCR, media transcription, web adapters, semantic deduplication, scheduler, Docker packaging, and a mutating review interface remain outside Phase 2. PDFs without embedded text fail extraction and remain inspectable. Exact SHA duplicates are flagged `duplicate`, never silently merged.

## Backup

Back up the entire configured data root, particularly `catalog/ptai_catalog.db`, `original/`, `processed/`, and configuration. Restore by stopping writers and restoring those paths together. Future vector indexes are rebuildable and are not authoritative.