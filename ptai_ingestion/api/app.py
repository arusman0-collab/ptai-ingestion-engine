"""Read-only Phase 1 operator API.

Each request opens its own SQLite connection.  This keeps FastAPI worker
threads independent while retaining SQLite's normal connection guarantees.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import Depends, FastAPI, HTTPException

from ..catalog import Catalog
from ..config import Settings, load_settings


SOURCE_FIELDS = (
    "source_id", "title", "speaker", "author", "date", "source_type",
    "publisher", "platform", "discovery_url", "rights_status",
    "archive_status", "sha256", "mime_type", "file_size", "created_at",
    "updated_at", "notes", "error_log",
)
QUEUE_FIELDS = (
    "id", "adapter", "platform", "title", "url", "possible_author",
    "source_type", "collection_slug", "rights_status", "status",
    "discovered_at", "source_id", "error",
)
EVENT_FIELDS = (
    "id", "created_at", "source_id", "pipeline_stage", "previous_state",
    "new_state", "status", "message", "error",
)


def _shape(row: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    """Return an allow-listed JSON object, never raw SQLite rows."""
    return {field: row[field] for field in fields}


def _counts(catalog: Catalog, table: str, state_column: str) -> dict[str, int]:
    rows = catalog.conn.execute(
        f"SELECT {state_column}, count(*) AS count FROM {table} GROUP BY {state_column}"
    ).fetchall()
    return {row[state_column]: row["count"] for row in rows}


def create_app(config_path: str | None = None) -> FastAPI:
    settings: Settings = load_settings(config_path)

    # Initialization is short-lived too; request handlers never retain it.
    initializer = Catalog(settings.database_path)
    try:
        initializer.migrate()
        initializer.ensure_collections(settings.collections)
    finally:
        initializer.close()

    app = FastAPI(title="PT-AI Ingestion Operator API", version="0.1.0")

    def get_catalog() -> Iterator[Catalog]:
        catalog = Catalog(settings.database_path)
        try:
            yield catalog
        finally:
            catalog.close()

    @app.get("/api/status")
    def status(catalog: Catalog = Depends(get_catalog)) -> dict[str, Any]:
        source_counts = _counts(catalog, "sources", "archive_status")
        queue_counts = _counts(catalog, "discovery_queue", "status")
        return {
            "sources": {"total": sum(source_counts.values()), "by_status": source_counts},
            "queue": {"total": sum(queue_counts.values()), "by_status": queue_counts},
        }

    @app.get("/api/sources")
    def sources(
        status: str | None = None, catalog: Catalog = Depends(get_catalog)
    ) -> dict[str, Any]:
        query = "SELECT * FROM sources"
        parameters: tuple[str, ...] = ()
        if status is not None:
            query += " WHERE archive_status=?"
            parameters = (status,)
        query += " ORDER BY source_id"
        items = [_shape(row, SOURCE_FIELDS) for row in catalog.conn.execute(query, parameters).fetchall()]
        return {"items": items, "total": len(items)}

    @app.get("/api/sources/{source_id}")
    def source(source_id: str, catalog: Catalog = Depends(get_catalog)) -> dict[str, Any]:
        record = catalog.source(source_id)
        if record is None:
            raise HTTPException(status_code=404, detail="source not found")
        events = catalog.conn.execute(
            "SELECT * FROM processing_events WHERE source_id=? ORDER BY id", (source_id,)
        ).fetchall()
        return {
            "source": _shape(record, SOURCE_FIELDS),
            "events": [_shape(event, EVENT_FIELDS) for event in events],
        }

    @app.get("/api/queue")
    def queue(
        status: str | None = None, catalog: Catalog = Depends(get_catalog)
    ) -> dict[str, Any]:
        query = "SELECT * FROM discovery_queue"
        parameters: tuple[str, ...] = ()
        if status is not None:
            query += " WHERE status=?"
            parameters = (status,)
        query += " ORDER BY id"
        items = [_shape(row, QUEUE_FIELDS) for row in catalog.conn.execute(query, parameters).fetchall()]
        return {"items": items, "total": len(items)}

    @app.get("/api/review")
    def review(catalog: Catalog = Depends(get_catalog)) -> dict[str, Any]:
        sources_for_review = catalog.conn.execute(
            """SELECT * FROM sources
               WHERE archive_status IN ('needs_review', 'rights_hold', 'extraction_failed', 'indexing_failed')
               ORDER BY source_id"""
        ).fetchall()
        rights_queue = catalog.conn.execute(
            "SELECT * FROM discovery_queue WHERE status='rights_hold' ORDER BY id"
        ).fetchall()
        source_items = [_shape(row, SOURCE_FIELDS) for row in sources_for_review]
        queue_candidates = [_shape(row, QUEUE_FIELDS) for row in rights_queue]
        return {
            "sources": source_items,
            "queue_candidates": queue_candidates,
            "total": len(source_items) + len(queue_candidates),
        }

    return app


app = create_app()