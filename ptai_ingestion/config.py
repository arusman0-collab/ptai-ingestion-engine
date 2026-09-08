from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class ChunkingSettings:
    max_size: int = 1800
    min_size: int = 300
    overlap: int = 150


@dataclass
class EmbeddingSettings:
    model: str = "nomic-embed-text"
    dimensions: int = 768


@dataclass
class QdrantSettings:
    url: str = "http://localhost:6333"
    collection: str = "ptai_sources"


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
        self.chunking = self.chunking if isinstance(self.chunking, ChunkingSettings) else ChunkingSettings(**self.chunking)
        self.embedding = self.embedding if isinstance(self.embedding, EmbeddingSettings) else EmbeddingSettings(**self.embedding)
        self.qdrant = self.qdrant if isinstance(self.qdrant, QdrantSettings) else QdrantSettings(**self.qdrant)
        self.ollama = self.ollama if isinstance(self.ollama, OllamaSettings) else OllamaSettings(**self.ollama)

def load_settings(path: str | Path | None = None) -> Settings:
    path = Path(path or os.getenv("PTAI_CONFIG", "config.yml"))
    values = yaml.safe_load(path.read_text()) if path.exists() else {}
    if os.getenv("PTAI_DATA_ROOT"):
        values["data_root"] = os.environ["PTAI_DATA_ROOT"]
    return Settings(**(values or {}))