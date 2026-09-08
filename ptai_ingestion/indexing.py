"""Authoritative archive-to-vector indexing orchestration."""
from __future__ import annotations
import uuid
from dataclasses import asdict
from typing import Any
from .catalog import Catalog, now
from .chunking import CHUNKING_VERSION, chunk_text
from .config import Settings
from .embeddings import EmbeddingService
from .vector import VectorRepository

def point_id(source_id: str, manifestation_id: int | None, chunk_index: int, chunking_version: str = CHUNKING_VERSION) -> str:
    value = "\x1f".join([source_id, str(manifestation_id or ""), str(chunk_index), chunking_version])
    return str(uuid.uuid5(uuid.UUID("9bcf6e5e-7b91-5d2e-aabc-8a27b2f4c3c5"), value))

class Indexer:
    def __init__(self, catalog: Catalog, settings: Settings, embeddings: EmbeddingService, vectors: VectorRepository):
        self.catalog, self.settings, self.embeddings, self.vectors = catalog, settings, embeddings, vectors
    def _source_row(self, source_id: str):
        row = self.catalog.conn.execute("""SELECT s.*, c.slug AS collection FROM sources s
            JOIN collections c ON c.id=s.collection_id WHERE s.source_id=?""", (source_id,)).fetchone()
        if not row: raise ValueError(f"unknown source: {source_id}")
        if not row["processed_path"]: raise ValueError(f"{source_id} has no processed archival text")
        return row
    def _build_points(self, source_id: str) -> list[dict]:
        row = self._source_row(source_id)
        text = open(row["processed_path"], encoding="utf-8").read()
        chunks = chunk_text(text, self.settings.chunking.max_chars, self.settings.chunking.min_chars, self.settings.chunking.overlap_chars)
        manifestation = self.catalog.conn.execute("""SELECT id FROM manifestations
            WHERE source_id=(SELECT id FROM sources WHERE source_id=?) ORDER BY id LIMIT 1""", (source_id,)).fetchone()
        manifestation_id = manifestation["id"] if manifestation else None
        vectors = self.embeddings.embed_documents([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks): raise RuntimeError("embedding backend returned an unexpected vector count")
        points=[]
        for chunk, vector in zip(chunks, vectors):
            payload: dict[str, Any] = {
                    "source_id": source_id, "manifestation_id": manifestation_id, "chunk_index": chunk.index,
                    "title": row["title"], "publisher": row["publisher"], "source_url": row["canonical_url"] or row["discovery_url"],
                    "language": row["language"], "text": chunk.text, "section_heading": chunk.section_heading,
                    "page": chunk.page, "timestamp": row["date"], "chunking_version": CHUNKING_VERSION,
                    "embedding_model": self.embeddings.model,
                    "embedding_version": getattr(self.settings.embedding, "version", None) or self.embeddings.model,
                    "embedding_dimensions": self.embeddings.dimensions,
                    "collection": row["collection"],
            }
            points.append({"id": point_id(source_id, manifestation_id, chunk.index), "vector": vector, "payload": payload})
        return points

    def index_source(self, source_id: str) -> int:
        row = self._source_row(source_id)
        try:
            # All fallible local/Ollama work happens before altering existing vectors.
            points = self._build_points(source_id)
            generation = self.generation()
            existing = self.catalog.conn.execute("""SELECT chunking_version,embedding_model,embedding_version,embedding_dimensions
                FROM source_index_versions WHERE source_id<>? LIMIT 1""", (source_id,)).fetchone()
            if existing and any(existing[key] != generation[key] for key in generation):
                raise RuntimeError("index generation differs from existing collection; run rebuild-index to avoid mixed vectors")
            self.vectors.ensure_collection(self.embeddings.dimensions, generation)
            self.vectors.replace_source(source_id, points)
            self.catalog.conn.execute("""INSERT INTO source_index_versions(source_id,chunking_version,embedding_model,embedding_version,embedding_dimensions,indexed_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET chunking_version=excluded.chunking_version,
                embedding_model=excluded.embedding_model,embedding_version=excluded.embedding_version,
                embedding_dimensions=excluded.embedding_dimensions,indexed_at=excluded.indexed_at""",
                (source_id, CHUNKING_VERSION, self.embeddings.model, generation["embedding_version"], self.embeddings.dimensions, now()))
            self.catalog.conn.commit()
            if row["archive_status"] != "indexed":
                self.catalog.transition(source_id, "indexed", "indexing", f"{len(points)} chunks indexed")
            else:
                self.catalog.event(source_id, "indexing", "indexed", "indexed", message=f"{len(points)} chunks reindexed")
            return len(points)
        except Exception as exc:
            # Preservation happened before indexing; record a retryable failure, never delete archives.
            self.catalog.conn.execute("UPDATE sources SET error_log=?,updated_at=? WHERE source_id=?", (str(exc), now(), source_id))
            self.catalog.conn.commit()
            current = self.catalog.source(source_id)["archive_status"]
            if current in {"cataloged", "indexed", "indexing_failed"}:
                self.catalog.transition(source_id, "indexing_failed", "indexing", str(exc), status="failed", error=str(exc))
            else:
                self.catalog.event(source_id, "indexing", current, current, status="failed", error=str(exc))
            raise
    def generation(self) -> dict[str, object]:
        return {"chunking_version": CHUNKING_VERSION, "embedding_model": self.embeddings.model,
                "embedding_version": getattr(self.settings.embedding, "version", None) or self.embeddings.model,
                "embedding_dimensions": self.embeddings.dimensions}
    def rebuild(self) -> int:
        rows=self.catalog.conn.execute("SELECT source_id FROM sources WHERE processed_path IS NOT NULL AND archive_status NOT IN ('duplicate','rights_hold')").fetchall()
        # Generate every embedding before the active index is touched.
        plans = [(row["source_id"], self._build_points(row["source_id"])) for row in rows]
        try:
            self.vectors.atomic_rebuild(plans, self.embeddings.dimensions, self.generation())
        except Exception as exc:
            self.catalog.event(None, "rebuild_index", status="failed", message="active index preserved", error=str(exc))
            raise
        for source_id, points in plans:
            source = self._source_row(source_id)
            generation = self.generation()
            self.catalog.conn.execute("""INSERT INTO source_index_versions(source_id,chunking_version,embedding_model,embedding_version,embedding_dimensions,indexed_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET chunking_version=excluded.chunking_version,
                embedding_model=excluded.embedding_model,embedding_version=excluded.embedding_version,
                embedding_dimensions=excluded.embedding_dimensions,indexed_at=excluded.indexed_at""",
                (source_id, CHUNKING_VERSION, self.embeddings.model, generation["embedding_version"], self.embeddings.dimensions, now()))
            self.catalog.conn.commit()
            if source["archive_status"] != "indexed":
                self.catalog.transition(source_id, "indexed", "indexing", f"{len(points)} chunks indexed by rebuild")
        return sum(len(points) for _, points in plans)