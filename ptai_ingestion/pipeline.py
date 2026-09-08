"""Phase 1 local archival pipeline."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from .catalog import Catalog, now
from .extraction.html import extract_html
from .extraction.pdf import extract_pdf
from .extraction.text import extract_text
from .hashing import sha256_file
from .storage import ArchiveStorage

BLOCKED_RIGHTS = {"unknown", "rights_hold", "restricted", "catalog_only_pending_review"}
EXTRACTORS = {".txt": extract_text, ".html": extract_html, ".htm": extract_html, ".pdf": extract_pdf}


class Pipeline:
    def __init__(self, catalog: Catalog, storage: ArchiveStorage):
        self.catalog = catalog
        self.storage = storage

    def discover(self, adapter) -> None:
        for candidate in adapter.discover():
            self.catalog.queue(**candidate)

    def process(self, source_id: str | None = None) -> None:
        query = "SELECT * FROM discovery_queue WHERE status='new'"
        parameters: tuple = ()
        if source_id:
            query += " AND source_id=?"
            parameters = (source_id,)
        for candidate in self.catalog.conn.execute(query, parameters).fetchall():
            self._process_item(candidate)

    def _process_item(self, candidate) -> None:
        if candidate["rights_status"] in BLOCKED_RIGHTS:
            self.catalog.conn.execute("UPDATE discovery_queue SET status='rights_hold' WHERE id=?", (candidate["id"],))
            self.catalog.conn.commit()
            self.catalog.event(None, "rights_gate", None, "rights_hold", "blocked", "acquisition requires permitted_archive")
            return

        source_id = candidate["source_id"] or self.catalog.allocate_source_id(candidate["collection_slug"])
        source_path = Path(candidate["local_path"])
        digest = sha256_file(source_path)
        collection = self.catalog.conn.execute(
            "SELECT id FROM collections WHERE slug=?", (candidate["collection_slug"],)
        ).fetchone()
        if collection is None:
            raise ValueError(f"unknown collection: {candidate['collection_slug']}")

        self.catalog.conn.execute(
            """INSERT OR IGNORE INTO sources
            (source_id,collection_id,title,source_type,platform,discovery_url,discovery_date,rights_status,
             archive_status,sha256,mime_type,file_size,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (source_id, collection["id"], candidate["title"], candidate["source_type"], candidate["platform"],
             candidate["url"], now(), candidate["rights_status"], "new", digest,
             mimetypes.guess_type(source_path.name)[0], source_path.stat().st_size, now(), now()),
        )
        self.catalog.conn.commit()

        duplicate = self.catalog.conn.execute(
            "SELECT source_id FROM sources WHERE sha256=? AND source_id<>?", (digest, source_id)
        ).fetchone()
        original, _ = self.storage.preserve_original(source_path, source_id)
        self.catalog.conn.execute(
            "UPDATE sources SET local_original_path=?, updated_at=? WHERE source_id=?",
            (str(original), now(), source_id),
        )
        self.catalog.conn.execute(
            "UPDATE discovery_queue SET source_id=?, status=? WHERE id=?",
            (source_id, "duplicate" if duplicate else "processing", candidate["id"]),
        )
        self.catalog.conn.commit()

        if duplicate:
            self.catalog.transition(source_id, "duplicate", "deduplication", f"exact SHA-256 duplicate of {duplicate['source_id']}")
            return

        self.catalog.transition(source_id, "verified", "verification")
        self.catalog.transition(source_id, "approved", "approval")
        self.catalog.transition(source_id, "acquired", "acquisition", "original preserved")
        try:
            extractor = EXTRACTORS[source_path.suffix.lower()]
            text, extraction = extractor(original)
            processed_path = self.storage.processed_path(source_id)
            processed_path.write_text(text, encoding="utf-8")
            metadata_path = self.storage.write_metadata(source_id, {
                "source_id": source_id,
                "original_path": str(original),
                "sha256": digest,
                "extraction": extraction,
                "discovery": json.loads(candidate["metadata_json"] or "{}"),
            })
            self.catalog.conn.execute(
                "UPDATE sources SET processed_path=?, metadata_path=?, notes=?, updated_at=? WHERE source_id=?",
                (str(processed_path), str(metadata_path), json.dumps(extraction), now(), source_id),
            )
            self.catalog.conn.execute(
                """INSERT INTO manifestations(source_id,kind,original_filename,extraction_method,page_count,created_at)
                VALUES((SELECT id FROM sources WHERE source_id=?),'original',?,?,?,?)""",
                (source_id, source_path.name, extraction["method"], extraction.get("page_count"), now()),
            )
            self.catalog.conn.commit()
            self.catalog.transition(source_id, "extracted", "extraction", json.dumps(extraction))
            self.catalog.transition(source_id, "cataloged", "catalog")
            self.catalog.conn.execute("UPDATE discovery_queue SET status='cataloged' WHERE id=?", (candidate["id"],))
            self.catalog.conn.commit()
        except Exception as exc:
            self.catalog.transition(source_id, "extraction_failed", "extraction", str(exc))
            self.catalog.event(source_id, "extraction", "acquired", "extraction_failed", "failed", error=str(exc))