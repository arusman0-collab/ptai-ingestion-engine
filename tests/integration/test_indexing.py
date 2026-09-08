import json
from pathlib import Path
from fastapi.testclient import TestClient

from ptai_ingestion.adapters.local_drop import LocalDropAdapter
from ptai_ingestion.api.app import create_app
from ptai_ingestion.catalog import Catalog
from ptai_ingestion.config import Settings
from ptai_ingestion.indexing import Indexer
from ptai_ingestion.pipeline import Pipeline
from ptai_ingestion.storage import ArchiveStorage
from ptai_ingestion.vector import InMemoryVectorRepository


class DeterministicEmbedding:
    model, dimensions = "test-embed", 2
    def embed_documents(self, texts):
        return [[float(len(text)), 1.0] for text in texts]
    def embed_query(self, query):
        return [float(len(query)), 1.0]


def setup_indexed(tmp_path):
    data, drop = tmp_path / "data", tmp_path / "drop"
    drop.mkdir()
    (drop / "a.txt").write_text("# Alpha\n\nUnique alpha archival evidence.")
    (drop / "b.txt").write_text("# Beta\n\nUnique beta archival evidence.")
    settings = Settings(data_root=data, embedding={"model": "test-embed", "dimensions": 2, "version": "test-v1"})
    catalog = Catalog(settings.database_path); catalog.migrate(); catalog.ensure_collections(settings.collections)
    pipeline = Pipeline(catalog, ArchiveStorage(data))
    pipeline.discover(LocalDropAdapter(drop)); pipeline.process()
    vectors, embedder = InMemoryVectorRepository(), DeterministicEmbedding()
    return settings, catalog, Indexer(catalog, settings, embedder, vectors), vectors, embedder


def test_local_sources_index_idempotently_and_rebuild_from_archive(tmp_path):
    _, catalog, indexer, vectors, _ = setup_indexed(tmp_path)
    ids = [row["source_id"] for row in catalog.conn.execute("SELECT source_id FROM sources ORDER BY source_id")]
    assert [indexer.index_source(source_id) for source_id in ids] == [1, 1]
    before_b = {key: value for key, value in vectors.points.items() if value["payload"]["source_id"] == ids[1]}
    assert indexer.index_source(ids[0]) == 1
    assert len(vectors.points) == 2
    assert before_b == {key: value for key, value in vectors.points.items() if value["payload"]["source_id"] == ids[1]}
    vectors.points.clear()
    assert indexer.rebuild() == 2
    assert len(vectors.points) == 2


def test_index_failure_preserves_authoritative_archive_and_records_state(tmp_path):
    _, catalog, indexer, _, _ = setup_indexed(tmp_path)
    source = catalog.conn.execute("SELECT * FROM sources ORDER BY source_id LIMIT 1").fetchone()
    original, processed, digest = Path(source["local_original_path"]).read_bytes(), Path(source["processed_path"]).read_text(), source["sha256"]
    class Broken:
        model, dimensions = "broken", 2
        def embed_documents(self, texts): raise RuntimeError("embedding unavailable")
        def embed_query(self, query): raise RuntimeError("embedding unavailable")
    indexer.embeddings = Broken()
    try: indexer.index_source(source["source_id"])
    except RuntimeError: pass
    row = catalog.source(source["source_id"])
    assert row["archive_status"] == "indexing_failed" and row["sha256"] == digest
    assert Path(row["local_original_path"]).read_bytes() == original
    assert Path(row["processed_path"]).read_text() == processed


def test_search_api_evidence_status_and_source_index_metadata(tmp_path):
    settings, catalog, indexer, vectors, embedder = setup_indexed(tmp_path)
    for row in catalog.conn.execute("SELECT source_id FROM sources"): indexer.index_source(row["source_id"])
    config = tmp_path / "config.yml"
    config.write_text(f"data_root: {settings.data_root}\nembedding:\n  model: test-embed\n  dimensions: 2\n  version: test-v1\n")
    client = TestClient(create_app(str(config), embeddings=embedder, vectors=vectors))
    response = client.post("/api/search", json={"query": "alpha", "limit": 1, "collection": "stephen-tong"})
    assert response.status_code == 200
    evidence = response.json()["evidence"][0]
    assert set(("score", "source_id", "text", "chunk_index", "source_url")).issubset(evidence)
    assert "answer" not in response.json() and "data/original" not in json.dumps(response.json())
    status = client.get("/api/index/status").json()
    assert status["indexed_sources"] == 2 and status["embedding_dimensions"] == 2 and status["qdrant"]["status"] == "ok"
    detail = client.get(f"/api/sources/{evidence['source_id']}").json()
    assert detail["source"]["index"]["embedding_version"] == "test-v1"


def test_atomic_rebuild_failure_preserves_active_vectors_and_archives(tmp_path):
    _, catalog, indexer, vectors, _ = setup_indexed(tmp_path)
    for row in catalog.conn.execute("SELECT source_id FROM sources"): indexer.index_source(row["source_id"])
    before = dict(vectors.points)
    rows = catalog.conn.execute("SELECT local_original_path,processed_path FROM sources").fetchall()
    vectors.fail_atomic_rebuild = True
    try: indexer.rebuild()
    except RuntimeError: pass
    else: assert False
    assert vectors.points == before
    assert all(Path(row["local_original_path"]).exists() and Path(row["processed_path"]).exists() for row in rows)
    assert catalog.conn.execute("SELECT count(*) FROM processing_events WHERE pipeline_stage='rebuild_index' AND status='failed'").fetchone()[0] == 1