import pytest

from ptai_ingestion.catalog import Catalog, normalize_url
from ptai_ingestion.config import load_settings
from ptai_ingestion.hashing import sha256_file
from ptai_ingestion.models import can_transition
from ptai_ingestion.storage import ArchiveStorage
from ptai_ingestion.pipeline import Pipeline


def catalog(tmp_path):
    instance = Catalog(tmp_path / "catalog.db")
    instance.migrate()
    instance.ensure_collections([
        {"slug": "stephen-tong", "name": "Stephen Tong", "source_prefix": "ST"},
        {"slug": "augustine", "name": "Augustine", "source_prefix": "AU"},
    ])
    return instance


def test_collection_aware_monotonic_source_ids_are_never_reused(tmp_path):
    instance = catalog(tmp_path)
    assert instance.allocate_source_id("stephen-tong") == "ST-000001"
    assert instance.allocate_source_id("augustine") == "AU-000001"
    assert instance.allocate_source_id("stephen-tong") == "ST-000002"


def test_url_normalization_and_candidate_deduplication(tmp_path):
    instance = catalog(tmp_path)
    instance.queue(adapter="local_drop", url="HTTPS://Example.test/article/?utm_source=newsletter&a=1", title="One")
    instance.queue(adapter="local_drop", url="https://example.test/article?a=1", title="Same")
    assert normalize_url("HTTPS://Example.test/article/?utm_source=x&a=1") == "https://example.test/article?a=1"
    assert instance.conn.execute("SELECT count(*) FROM discovery_queue").fetchone()[0] == 1


def test_lifecycle_transition_and_event_recording(tmp_path):
    instance = catalog(tmp_path)
    source_id = instance.allocate_source_id("stephen-tong")
    collection_id = instance.conn.execute("SELECT id FROM collections WHERE slug='stephen-tong'").fetchone()[0]
    instance.conn.execute(
        "INSERT INTO sources(source_id,collection_id,rights_status,archive_status,created_at,updated_at) VALUES(?,?,?,'new',?,?)",
        (source_id, collection_id, "permitted_archive", "now", "now"),
    )
    instance.conn.commit()
    instance.transition(source_id, "verified", "verification")
    event = instance.conn.execute("SELECT previous_state,new_state,pipeline_stage FROM processing_events").fetchone()
    assert tuple(event) == ("new", "verified", "verification")
    assert not can_transition("new", "cataloged")
    assert not can_transition("not_a_state", "verified")


def test_sha_integrity_and_original_non_overwrite(tmp_path):
    source = tmp_path / "x.txt"
    source.write_text("one")
    storage = ArchiveStorage(tmp_path / "data")
    archived, initial_hash = storage.preserve_original(source, "ST-000001")
    source.write_text("two")
    assert sha256_file(archived) == initial_hash
    assert archived.read_text() == "one"


def test_config_data_root_environment_override(tmp_path, monkeypatch):
    config = tmp_path / "config.yml"
    config.write_text("data_root: ./configured-data\ncollections: []\n")
    monkeypatch.setenv("PTAI_DATA_ROOT", str(tmp_path / "environment-data"))
    settings = load_settings(config)
    assert settings.data_root == tmp_path / "environment-data"
    assert settings.database_path == tmp_path / "environment-data" / "catalog" / "ptai_catalog.db"


def test_config_example_loads_with_inert_phase_two_placeholders():
    settings = load_settings("config.example.yml")
    assert settings.chunking.max_size == 1800
    assert settings.embedding.dimensions == 768
    assert settings.qdrant.collection == "ptai_sources"
    assert settings.ollama.url == "http://localhost:11434"


def test_targeting_unknown_queue_id_is_an_explicit_error(tmp_path):
    instance = catalog(tmp_path)
    pipeline = Pipeline(instance, ArchiveStorage(tmp_path / "data"))
    with pytest.raises(ValueError, match="no new queue candidate with id 999"):
        pipeline.process(queue_id=999)