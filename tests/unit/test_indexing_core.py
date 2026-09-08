from ptai_ingestion.chunking import chunk_text
from ptai_ingestion.embeddings import DOCUMENT_PREFIX, QUERY_PREFIX, OllamaEmbeddingService
from ptai_ingestion.indexing import point_id
from ptai_ingestion.vector import InMemoryVectorRepository, VectorConfigurationMismatch
from ptai_ingestion.vector import QdrantRepository
from ptai_ingestion.config import Settings
import uuid


def test_paragraph_chunking_is_deterministic_and_prefers_boundaries():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    first = chunk_text(text, max_chars=35, min_chars=5, overlap_chars=0)
    second = chunk_text(text, max_chars=35, min_chars=5, overlap_chars=0)
    assert first == second
    assert first[0].text == "First paragraph.\n\nSecond paragraph."
    assert first[1].text == "Third paragraph."


def test_stable_point_ids_include_source_manifestation_index_and_version():
    assert point_id("ST-1", 2, 0, "v1") == point_id("ST-1", 2, 0, "v1")
    assert point_id("ST-1", 2, 0, "v1") != point_id("ST-2", 2, 0, "v1")
    assert point_id("ST-1", 2, 0, "v1") != point_id("ST-1", 2, 0, "v2")
    assert uuid.UUID(point_id("ST-1", 2, 0, "v1")).version == 5


def test_embedding_prefixes_are_distinct_for_asymmetric_retrieval():
    assert DOCUMENT_PREFIX == "search_document: "
    assert QUERY_PREFIX == "search_query: "
    assert DOCUMENT_PREFIX != QUERY_PREFIX


def test_embedding_service_actually_invokes_document_and_query_prefixes():
    class RecordingEmbedding(OllamaEmbeddingService):
        def _embed(self, values):
            self.values = values
            return [[0.0] for _ in values]
    service = RecordingEmbedding("http://unused", "test", 1)
    service.embed_documents(["document"])
    assert service.values == ["search_document: document"]
    service.embed_query("question")
    assert service.values == ["search_query: question"]


def test_in_memory_repository_replaces_only_requested_source():
    repo = InMemoryVectorRepository()
    repo.ensure_collection(2)
    repo.replace_source("A", [{"id": "a", "vector": [1, 0], "payload": {"source_id": "A"}}])
    repo.replace_source("B", [{"id": "b", "vector": [0, 1], "payload": {"source_id": "B"}}])
    repo.replace_source("A", [{"id": "a2", "vector": [1, 0], "payload": {"source_id": "A"}}])
    assert set(repo.points) == {"a2", "b"}


def test_qdrant_http_validates_configuration_generation_and_wait(monkeypatch):
    calls = []
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            if calls[-1][1].endswith("/points/scroll"):
                return {"result": {"points": [{"payload": {"chunking_version": "v1", "embedding_model": "m", "embedding_version": "1", "embedding_dimensions": 2}}]}}
            return {"result": {"config": {"params": {"vectors": {"size": 2, "distance": "Cosine"}}}}}
    def request(method, url, **kwargs):
        calls.append((method, url, kwargs)); return Response()
    monkeypatch.setattr("ptai_ingestion.vector.httpx.request", request)
    repo = QdrantRepository("http://qdrant", "items")
    generation = {"chunking_version": "v1", "embedding_model": "m", "embedding_version": "1", "embedding_dimensions": 2}
    repo.ensure_collection(2, generation)
    repo.replace_source("A", [{"id": "00000000-0000-5000-8000-000000000000", "vector": [0, 1], "payload": {"source_id": "A"}}])
    assert any("/points?wait=true" in call[1] for call in calls)
    assert any("/points/delete?wait=true" in call[1] for call in calls)
    assert calls[-1][2]["json"]["filter"]["must_not"][0]["has_id"]


def test_qdrant_http_rejects_dimension_or_generation_mismatch(monkeypatch):
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"result": {"config": {"params": {"vectors": {"size": 3, "distance": "Dot"}}}}}
    monkeypatch.setattr("ptai_ingestion.vector.httpx.request", lambda *args, **kwargs: Response())
    try: QdrantRepository("http://q", "c").ensure_collection(2, {"chunking_version":"v","embedding_model":"m","embedding_version":"1","embedding_dimensions":2})
    except VectorConfigurationMismatch: pass
    else: assert False


def test_qdrant_http_rejects_existing_generation_mismatch(monkeypatch):
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"result": {"points": [{"payload": {"chunking_version":"old", "embedding_model":"m", "embedding_version":"1", "embedding_dimensions":2}}]}} if call[0].endswith("/scroll") else {"result": {"config": {"params": {"vectors": {"size":2, "distance":"Cosine"}}}}}
    def request(method, url, **kwargs):
        call[0] = url
        return Response()
    call = [""]
    monkeypatch.setattr("ptai_ingestion.vector.httpx.request", request)
    try: QdrantRepository("http://q", "c").ensure_collection(2, {"chunking_version":"new","embedding_model":"m","embedding_version":"1","embedding_dimensions":2})
    except VectorConfigurationMismatch: pass
    else: assert False


def test_qdrant_http_rejects_generation_mismatch_on_later_scroll_page(monkeypatch):
    calls = []
    generation = {
        "chunking_version": "v1", "embedding_model": "m",
        "embedding_version": "1", "embedding_dimensions": 2,
    }

    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            url, request = calls[-1]
            if url.endswith("/points/scroll"):
                if "offset" not in request:
                    return {"result": {"points": [{"payload": generation}], "next_page_offset": "next"}}
                return {"result": {"points": [{"payload": {**generation, "embedding_model": "other"}}]}}
            return {"result": {"config": {"params": {"vectors": {"size": 2, "distance": "Cosine"}}}}}

    def request(method, url, **kwargs):
        calls.append((url, kwargs.get("json", {})))
        return Response()

    monkeypatch.setattr("ptai_ingestion.vector.httpx.request", request)
    try:
        QdrantRepository("http://q", "c").ensure_collection(2, generation)
    except VectorConfigurationMismatch:
        pass
    else:
        assert False


def test_phase_two_configuration_validation():
    try: Settings(chunking={"max_chars": 10, "min_chars": 11})
    except ValueError: pass
    else: assert False


def test_page_markers_and_headings_are_preserved_deterministically():
    chunks = chunk_text("[Page 1]\n# FIRST\n\nOne.\n\n[Page 2]\n# SECOND\n\nTwo.", 100, 1, 0)
    assert [(chunk.page, chunk.section_heading, chunk.text) for chunk in chunks] == [
        (1, "FIRST", "One."), (2, "SECOND", "Two.")]
    try: Settings(embedding={"model": "", "dimensions": 0})
    except ValueError: pass
    else: assert False