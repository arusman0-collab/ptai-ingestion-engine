"""SQLite catalog, migrations, lifecycle audit trail, and queue operations."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import TERMINAL_HOLDS, can_transition

TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_url(url: str | None) -> str | None:
    """Normalize a URL for candidate identity, omitting common tracking fields."""
    if not url:
        return None
    parts = urlsplit(url.strip())
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMETERS]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), ""))


class Catalog:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")

    def migrate(self, migrations: Path | None = None) -> None:
        migrations = migrations or Path(__file__).parent / "migrations"
        self.conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        for migration in sorted(migrations.glob("*.sql")):
            installed = self.conn.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (migration.name,)).fetchone()
            if not installed:
                self.conn.executescript(migration.read_text())
                self.conn.execute("INSERT INTO schema_migrations VALUES (?, ?)", (migration.name, now()))
                self.conn.commit()

    def ensure_collections(self, collections: list[dict]) -> None:
        for collection in collections:
            self.conn.execute(
                "INSERT OR IGNORE INTO collections(slug,name,source_prefix,created_at) VALUES(?,?,?,?)",
                (collection["slug"], collection["name"], collection["source_prefix"], now()),
            )
        self.conn.commit()

    def allocate_source_id(self, slug: str) -> str:
        """Allocate a never-reused sequential ID within one collection namespace."""
        with self.conn:
            collection = self.conn.execute(
                "SELECT id, source_prefix, next_source_number FROM collections WHERE slug = ?", (slug,)
            ).fetchone()
            if collection is None:
                raise ValueError(f"unknown collection: {slug}")
            self.conn.execute("UPDATE collections SET next_source_number = next_source_number + 1 WHERE id = ?", (collection["id"],))
        return f"{collection['source_prefix']}-{collection['next_source_number']:06d}"

    def event(self, source_id, stage, previous=None, new=None, status="ok", message=None, error=None) -> None:
        self.conn.execute(
            """INSERT INTO processing_events
            (created_at,source_id,pipeline_stage,previous_state,new_state,status,message,error,software_version)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (now(), source_id, stage, previous, new, status, message, error, "0.1.0"),
        )
        self.conn.commit()

    def queue(self, **item) -> None:
        normalized_url = normalize_url(item.get("normalized_url") or item.get("url"))
        self.conn.execute(
            """INSERT OR IGNORE INTO discovery_queue
            (adapter,platform,title,url,normalized_url,local_path,possible_author,source_type,collection_slug,
             rights_status,status,metadata_json,discovered_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (item["adapter"], item.get("platform", "local"), item.get("title"), item.get("url"), normalized_url,
             item.get("local_path"), item.get("possible_author"), item.get("source_type"),
             item.get("collection_slug", "stephen-tong"), item.get("rights_status", "unknown"), "new",
             json.dumps(item.get("metadata", {})), now()),
        )
        self.conn.commit()

    def source(self, source_id: str):
        return self.conn.execute("SELECT * FROM sources WHERE source_id = ?", (source_id,)).fetchone()

    def transition(self, source_id: str, new: str, stage: str, message: str | None = None) -> None:
        source = self.source(source_id)
        if source is None:
            raise ValueError(f"unknown source: {source_id}")
        old = source["archive_status"]
        if old in {item.value for item in TERMINAL_HOLDS}:
            raise PermissionError(f"{source_id} is {old}; human review required")
        if not can_transition(old, new):
            raise ValueError(f"invalid lifecycle transition {old} -> {new}")
        self.conn.execute("UPDATE sources SET archive_status=?, updated_at=? WHERE source_id=?", (new, now(), source_id))
        self.conn.commit()
        self.event(source_id, stage, old, new, message=message)

    def counts(self) -> dict[str, int]:
        return dict(self.conn.execute("SELECT archive_status, count(*) FROM sources GROUP BY archive_status").fetchall())