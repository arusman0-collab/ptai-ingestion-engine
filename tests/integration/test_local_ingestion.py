import json

from ptai_ingestion.adapters.local_drop import LocalDropAdapter
from ptai_ingestion.catalog import Catalog
from ptai_ingestion.config import Settings
from ptai_ingestion.pipeline import Pipeline
from ptai_ingestion.storage import ArchiveStorage


def build_pipeline(tmp_path):
    settings = Settings(data_root=tmp_path / "data")
    catalog = Catalog(settings.database_path)
    catalog.migrate()
    catalog.ensure_collections(settings.collections)
    return catalog, Pipeline(catalog, ArchiveStorage(settings.data_root))


def test_local_text_ingests_with_provenance_and_audit_history(tmp_path):
    drop = tmp_path / "drop"
    drop.mkdir()
    (drop / "sermon.txt").write_text("Preserved source text.")
    catalog, pipeline = build_pipeline(tmp_path)
    pipeline.discover(LocalDropAdapter(drop))
    pipeline.process()

    row = catalog.conn.execute("SELECT * FROM sources").fetchone()
    assert row["archive_status"] == "cataloged"
    assert open(row["processed_path"], encoding="utf-8").read() == "Preserved source text."
    metadata = json.loads(open(row["metadata_path"], encoding="utf-8").read())
    assert metadata["source_id"] == row["source_id"]
    assert metadata["sha256"] == row["sha256"]
    assert catalog.conn.execute("SELECT count(*) FROM processing_events WHERE source_id=?", (row["source_id"],)).fetchone()[0] >= 5


def test_exact_binary_duplicate_is_flagged_not_silently_merged(tmp_path):
    drop = tmp_path / "drop"
    drop.mkdir()
    (drop / "one.txt").write_text("same artifact")
    (drop / "two.txt").write_text("same artifact")
    catalog, pipeline = build_pipeline(tmp_path)
    pipeline.discover(LocalDropAdapter(drop))
    pipeline.process()
    rows = catalog.conn.execute("SELECT source_id,archive_status FROM sources ORDER BY source_id").fetchall()
    assert len(rows) == 2
    assert {row["archive_status"] for row in rows} == {"cataloged", "duplicate"}
    assert catalog.conn.execute("SELECT count(*) FROM processing_events WHERE pipeline_stage='deduplication'").fetchone()[0] == 1


def test_rights_hold_blocks_before_acquisition(tmp_path):
    drop = tmp_path / "drop"
    drop.mkdir()
    (drop / "restricted.txt").write_text("must not archive")
    catalog, pipeline = build_pipeline(tmp_path)
    pipeline.discover(LocalDropAdapter(drop, rights_status="rights_hold"))
    pipeline.process()
    assert catalog.conn.execute("SELECT count(*) FROM sources").fetchone()[0] == 0
    assert not list((tmp_path / "data" / "original").rglob("*"))
    assert catalog.conn.execute("SELECT status FROM discovery_queue").fetchone()[0] == "rights_hold"