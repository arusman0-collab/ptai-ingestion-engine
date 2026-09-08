"""Read-only Phase 1 operator API.

Each request opens its own SQLite connection.  This keeps FastAPI worker
threads independent while retaining SQLite's normal connection guarantees.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..catalog import Catalog
from ..config import Settings, load_settings
from ..embeddings import OllamaEmbeddingService, EmbeddingService
from ..vector import QdrantRepository, VectorRepository


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


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=8, ge=1, le=100)
    collection: str | None = None

def create_app(config_path: str | None = None, *, embeddings: EmbeddingService | None = None,
               vectors: VectorRepository | None = None) -> FastAPI:
    settings: Settings = load_settings(config_path)

    # Initialization is short-lived too; request handlers never retain it.
    initializer = Catalog(settings.database_path)
    try:
        initializer.migrate()
        initializer.ensure_collections(settings.collections)
    finally:
        initializer.close()

    app = FastAPI(title="PT-AI Ingestion Operator API", version="0.1.0")
    embedding_service = embeddings or OllamaEmbeddingService(settings.ollama.url, settings.embedding.model, settings.embedding.dimensions)
    vector_repository = vectors or QdrantRepository(settings.qdrant.url, settings.qdrant.collection)

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
        index_version = catalog.conn.execute("SELECT chunking_version,embedding_model,embedding_version,embedding_dimensions,indexed_at FROM source_index_versions WHERE source_id=?", (source_id,)).fetchone()
        return {
            "source": {**_shape(record, SOURCE_FIELDS), "index": dict(index_version) if index_version else None},
            "events": [_shape(event, EVENT_FIELDS) for event in events],
        }

    @app.get("/api/index/status")
    def index_status(catalog: Catalog = Depends(get_catalog)) -> dict[str, Any]:
        indexed = catalog.conn.execute("SELECT count(*) FROM sources WHERE archive_status='indexed'").fetchone()[0]
        failures = catalog.conn.execute("SELECT count(*) FROM sources WHERE archive_status='indexing_failed'").fetchone()[0]
        try:
            health = vector_repository.health()
        except Exception as exc:
            health = {"status": "unavailable", "collection": settings.qdrant.collection, "url": settings.qdrant.url, "error": str(exc)}
        return {"indexed_sources": indexed, "index_failures": failures, "embedding_model": settings.embedding.model,
                "embedding_dimensions": settings.embedding.dimensions, "qdrant": health}

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

    @app.post("/api/search")
    def search(request: SearchRequest) -> dict[str, Any]:
        """Evidence retrieval only: no answer generation or reasoning-model call."""
        try:
            results = vector_repository.search(embedding_service.embed_query(request.query), request.limit, request.collection)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"search unavailable: {exc}") from exc
        allowed = ("source_id", "manifestation_id", "title", "chunk_index", "text", "publisher",
                   "source_url", "language", "section_heading", "page", "timestamp")
        return {"evidence": [{"score": item["score"], **{key: item.get("payload", {}).get(key) for key in allowed}}
                             for item in results]}

    return app


app = create_app()