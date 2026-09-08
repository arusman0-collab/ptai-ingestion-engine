from pathlib import Path

from fastapi.testclient import TestClient

from ptai_ingestion.adapters.local_drop import LocalDropAdapter
from ptai_ingestion.api.app import create_app
from ptai_ingestion.catalog import Catalog
from ptai_ingestion.config import Settings
from ptai_ingestion.pipeline import Pipeline
from ptai_ingestion.storage import ArchiveStorage


def _services(tmp_path: Path):
    settings = Settings(data_root=tmp_path / "data")
    catalog = Catalog(settings.database_path)
    catalog.migrate()
    catalog.ensure_collections(settings.collections)
    return settings, catalog, Pipeline(catalog, ArchiveStorage(settings.data_root))


def _client(tmp_path: Path) -> TestClient:
    config = tmp_path / "config.yml"
    config.write_text(f"data_root: {tmp_path / 'data'}\n")
    return TestClient(create_app(str(config)))


def test_operator_api_reports_real_ingested_source_without_archive_contents(tmp_path):
    drop = tmp_path / "drop"
    drop.mkdir()
    (drop / "sermon.txt").write_text("Copyrighted archive text must not be returned.")
    _, catalog, pipeline = _services(tmp_path)
    pipeline.discover(LocalDropAdapter(drop))
    pipeline.process()
    source_id = catalog.conn.execute("SELECT source_id FROM sources").fetchone()["source_id"]

    with _client(tmp_path) as client:
        status = client.get("/api/status")
        sources = client.get("/api/sources")
        queue = client.get("/api/queue")
        detail = client.get(f"/api/sources/{source_id}")
        review = client.get("/api/review")

    assert status.status_code == sources.status_code == queue.status_code == review.status_code == 200
    assert status.json()["sources"]["by_status"]["cataloged"] == 1
    assert sources.json()["items"][0]["source_id"] == source_id
    assert queue.json()["items"][0]["source_id"] == source_id
    assert detail.status_code == 200
    assert detail.json()["source"]["source_id"] == source_id
    assert "Copyrighted archive text" not in detail.text
    assert "local_original_path" not in detail.text
    assert "processed_path" not in detail.text
    assert review.json()["total"] == 0


def test_review_exposes_rights_hold_queue_candidate(tmp_path):
    drop = tmp_path / "drop"
    drop.mkdir()
    (drop / "held.txt").write_text("not permitted")
    _, catalog, pipeline = _services(tmp_path)
    pipeline.discover(LocalDropAdapter(drop, rights_status="rights_hold"))
    pipeline.process()

    with _client(tmp_path) as client:
        response = client.get("/api/review")

    assert response.status_code == 200
    candidate = response.json()["queue_candidates"][0]
    assert candidate["status"] == "rights_hold"
    assert candidate["title"] == "held"
    assert catalog.conn.execute("SELECT count(*) FROM sources").fetchone()[0] == 0


def test_review_exposes_extraction_failure_once_with_error_detail(tmp_path):
    drop = tmp_path / "drop"
    drop.mkdir()
    (drop / "broken.pdf").write_bytes(b"not a PDF")
    _, catalog, pipeline = _services(tmp_path)
    pipeline.discover(LocalDropAdapter(drop))
    pipeline.process()

    source_id = catalog.conn.execute("SELECT source_id FROM sources").fetchone()["source_id"]
    events = catalog.conn.execute(
        "SELECT * FROM processing_events WHERE source_id=? AND new_state='extraction_failed'",
        (source_id,),
    ).fetchall()
    assert len(events) == 1
    assert events[0]["status"] == "failed"
    assert events[0]["error"]

    with _client(tmp_path) as client:
        response = client.get("/api/review")
        detail = client.get(f"/api/sources/{source_id}")

    assert response.status_code == 200
    assert response.json()["sources"][0]["archive_status"] == "extraction_failed"
    assert response.json()["sources"][0]["error_log"]
    assert detail.json()["events"][-1]["error"]