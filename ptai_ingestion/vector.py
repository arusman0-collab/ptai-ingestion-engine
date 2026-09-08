"""Dedicated Qdrant repository; application code never calls Qdrant directly."""
from __future__ import annotations
from typing import Any, Protocol
import httpx
import uuid

class VectorConfigurationMismatch(RuntimeError): pass
class VectorRepository(Protocol):
    def ensure_collection(self, dimensions: int, generation: dict | None = None) -> None: ...
    def replace_source(self, source_id: str, points: list[dict]) -> None: ...
    def search(self, vector: list[float], limit: int, collection: str | None = None) -> list[dict]: ...
    def recreate(self, dimensions: int, generation: dict | None = None) -> None: ...
    def health(self) -> dict: ...
    def atomic_rebuild(self, plans: list[tuple[str, list[dict]]], dimensions: int, generation: dict) -> None: ...

class QdrantRepository:
    def __init__(self, url: str, collection: str):
        self.url, self.collection = url.rstrip("/"), collection
    def _request(self, method: str, suffix: str, **kwargs):
        response = httpx.request(method, f"{self.url}/collections/{self.collection}{suffix}", timeout=30, **kwargs)
        if response.status_code == 404: return None
        response.raise_for_status(); return response.json()
    def ensure_collection(self, dimensions: int, generation: dict | None = None) -> None:
        existing = self._request("GET", "")
        if existing is None:
            # Establish the configured logical name as an alias from day one.
            staging = f"{self.collection}__staging_{uuid.uuid4().hex}"
            stage = QdrantRepository(self.url, staging)
            stage._request("PUT", "", json={"vectors": {"size": dimensions, "distance": "Cosine"}})
            response = httpx.post(f"{self.url}/aliases?wait=true", json={"actions": [
                {"create_alias": {"collection_name": staging, "alias_name": self.collection}}]}, timeout=30)
            response.raise_for_status()
            return
        vectors = existing["result"]["config"]["params"]["vectors"]
        if isinstance(vectors, dict) and "size" in vectors:
            size, distance = vectors["size"], vectors["distance"]
        else:
            raise VectorConfigurationMismatch("named Qdrant vectors are incompatible with PT-AI collection")
        if size != dimensions or distance.lower() != "cosine":
            raise VectorConfigurationMismatch(f"Qdrant collection {self.collection!r} is {size}/{distance}; expected {dimensions}/Cosine. Refusing to destroy it.")
        # Collection configuration alone cannot express model/chunker generation.
        # Inspect every real point (not a searchable sentinel) before accepting it,
        # so a partially mixed or corrupt collection cannot pass by sampling.
        if generation:
            offset = None
            while True:
                request = {
                    "limit": 100,
                    "with_payload": [
                        "chunking_version", "embedding_model",
                        "embedding_version", "embedding_dimensions",
                    ],
                    "with_vector": False,
                }
                if offset is not None:
                    request["offset"] = offset
                page = self._request("POST", "/points/scroll", json=request)
                result = page["result"] if page else {"points": []}
                for point in result.get("points", []):
                    payload = point.get("payload", {})
                    if any(payload.get(key) != value for key, value in generation.items()):
                        raise VectorConfigurationMismatch(
                            "Qdrant collection contains incompatible or unversioned "
                            "vector generation; run rebuild-index"
                        )
                offset = result.get("next_page_offset")
                if offset is None:
                    break
    def replace_source(self, source_id: str, points: list[dict]) -> None:
        # Upsert first.  Then remove only old IDs for this source; a failed upsert
        # therefore leaves the prior source representation searchable.
        if points: self._request("PUT", "/points?wait=true", json={"points": points})
        ids = [point["id"] for point in points]
        self._request("POST", "/points/delete?wait=true", json={"filter": {"must": [{"key":"source_id","match":{"value":source_id}}],
            "must_not": [{"has_id": ids}]}})
    def search(self, vector: list[float], limit: int, collection: str | None = None) -> list[dict]:
        filters = [] if not collection else [{"key": "collection", "match": {"value": collection}}]
        result = self._request("POST", "/points/search", json={"vector": vector, "limit": limit, "with_payload": True,
            **({"filter":{"must":filters}} if filters else {})})
        return result["result"]
    def recreate(self, dimensions: int, generation: dict | None = None) -> None:
        self._request("DELETE", "?wait=true")
        self.ensure_collection(dimensions, generation)
    def health(self) -> dict:
        try:
            response = httpx.get(f"{self.url}/healthz", timeout=3)
            response.raise_for_status()
            return {"status": "ok", "collection": self.collection, "url": self.url}
        except Exception as exc:
            return {"status": "unavailable", "collection": self.collection, "url": self.url, "error": str(exc)}
    def atomic_rebuild(self, plans, dimensions, generation) -> None:
        # `collection` is deliberately a logical alias. A pre-Phase-2 physical
        # collection with that name cannot be converted safely without operator
        # action, so refuse rather than deleting it.
        aliases = httpx.get(f"{self.url}/aliases", timeout=30); aliases.raise_for_status()
        names = {item["alias_name"] for item in aliases.json().get("result", {}).get("aliases", [])}
        direct = self._request("GET", "")
        if self.collection not in names and direct is not None:
            raise VectorConfigurationMismatch(f"{self.collection!r} is a physical collection; migrate it to an alias or delete it, then rebuild-index")
        staging = f"{self.collection}__staging_{uuid.uuid4().hex}"
        stage = QdrantRepository(self.url, staging)
        try:
            stage.ensure_collection(dimensions)
            points = [point for _, source_points in plans for point in source_points]
            if points: stage._request("PUT", "/points?wait=true", json={"points": points})
            count = stage._request("POST", "/points/count", json={"exact": True})["result"]["count"]
            if count != len(points): raise RuntimeError(f"staging count {count} does not match expected {len(points)}")
            actions = []
            if self.collection in names: actions.append({"delete_alias": {"alias_name": self.collection}})
            actions.append({"create_alias": {"collection_name": staging, "alias_name": self.collection}})
            result = httpx.post(f"{self.url}/aliases?wait=true", json={"actions": actions}, timeout=30)
            result.raise_for_status()
        except Exception:
            stage._request("DELETE", "?wait=true")
            raise

class InMemoryVectorRepository:
    """Controlled test double with Qdrant's source replacement semantics."""
    def __init__(self): self.dimensions=None; self.points: dict[str, dict] = {}; self.generation=None
    def ensure_collection(self, dimensions, generation=None):
        if self.dimensions is not None and self.dimensions != dimensions: raise VectorConfigurationMismatch("dimension mismatch")
        if self.generation is not None and generation is not None and self.generation != generation: raise VectorConfigurationMismatch("generation mismatch; rebuild required")
        self.dimensions, self.generation = dimensions, generation or self.generation
    def recreate(self, dimensions, generation=None): self.dimensions=dimensions; self.generation=generation; self.points={}
    def replace_source(self, source_id, points):
        self.points={k:v for k,v in self.points.items() if v["payload"]["source_id"] != source_id}
        self.points.update({str(p["id"]):p for p in points})
    def search(self, vector, limit, collection=None):
        rows=[{"id":k,"score":sum(a*b for a,b in zip(vector,p["vector"])),"payload":p["payload"]} for k,p in self.points.items()
              if collection is None or p["payload"].get("collection")==collection]
        return sorted(rows,key=lambda x:x["score"],reverse=True)[:limit]
    def health(self): return {"status":"ok", "collection":"in-memory", "url":"memory://"}
    def atomic_rebuild(self, plans, dimensions, generation):
        if getattr(self, "fail_atomic_rebuild", False):
            raise RuntimeError("injected atomic rebuild failure")
        # Build a separate map and assign only after every plan was accepted.
        replacement = {}
        for _, points in plans:
            replacement.update({str(point["id"]): point for point in points})
        self.dimensions, self.generation, self.points = dimensions, generation, replacement