from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class ChunkingSettings:
    max_chars: int = 1800
    min_chars: int = 300
    overlap_chars: int = 150

    def __post_init__(self):
        if self.max_chars <= 0 or self.min_chars < 0 or self.overlap_chars < 0:
            raise ValueError("chunking sizes must be non-negative and max_chars positive")
        if self.min_chars > self.max_chars:
            raise ValueError("chunking.min_chars cannot exceed max_chars")
        if self.overlap_chars >= self.max_chars:
            raise ValueError("chunking.overlap_chars must be less than max_chars")

    # Backward-compatible Phase 1 read aliases; new configuration uses explicit units.
    @property
    def max_size(self) -> int: return self.max_chars
    @property
    def min_size(self) -> int: return self.min_chars
    @property
    def overlap(self) -> int: return self.overlap_chars


@dataclass
class EmbeddingSettings:
    model: str = "nomic-embed-text"
    dimensions: int = 768
    version: str | None = None

    def __post_init__(self):
        if not self.model or self.dimensions <= 0:
            raise ValueError("embedding.model and a positive embedding.dimensions are required")


@dataclass
class QdrantSettings:
    url: str = "http://localhost:6333"
    collection: str = "ptai_sources"

    def __post_init__(self):
        if not self.url.startswith(("http://", "https://")) or not self.collection:
            raise ValueError("qdrant.url must be HTTP(S) and qdrant.collection is required")


@dataclass
class OllamaSettings:
    url: str = "http://localhost:11434"


@dataclass
class Settings:
    environment: str = "development"
    data_root: Path = Path("./data")
    database_path: Path | None = None
    logging_level: str = "INFO"
    collections: list[dict] = field(default_factory=lambda: [{"slug":"stephen-tong","name":"Stephen Tong","source_prefix":"ST"}])
    approved_sources: list[dict] = field(default_factory=list)
    chunking: ChunkingSettings | dict = field(default_factory=ChunkingSettings)
    embedding: EmbeddingSettings | dict = field(default_factory=EmbeddingSettings)
    qdrant: QdrantSettings | dict = field(default_factory=QdrantSettings)
    ollama: OllamaSettings | dict = field(default_factory=OllamaSettings)

    def __post_init__(self):
        self.data_root = Path(self.data_root)
        self.database_path = Path(self.database_path or self.data_root / "catalog" / "ptai_catalog.db")
        if isinstance(self.chunking, dict):
            # Phase 1 spelling remains readable, while Phase 2 writes the explicit units.
            self.chunking = ChunkingSettings(**{
                {"max_size": "max_chars", "min_size": "min_chars", "overlap": "overlap_chars"}.get(k, k): v
                for k, v in self.chunking.items()
            })
        self.embedding = self.embedding if isinstance(self.embedding, EmbeddingSettings) else EmbeddingSettings(**self.embedding)
        self.qdrant = self.qdrant if isinstance(self.qdrant, QdrantSettings) else QdrantSettings(**self.qdrant)
        self.ollama = self.ollama if isinstance(self.ollama, OllamaSettings) else OllamaSettings(**self.ollama)

def load_settings(path: str | Path | None = None) -> Settings:
    path = Path(path or os.getenv("PTAI_CONFIG", "config.yml"))
    values = yaml.safe_load(path.read_text()) if path.exists() else {}
    if os.getenv("PTAI_DATA_ROOT"):
        values["data_root"] = os.environ["PTAI_DATA_ROOT"]
    return Settings(**(values or {}))