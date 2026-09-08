from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
import yaml

@dataclass
class Settings:
    environment: str = "development"
    data_root: Path = Path("./data")
    database_path: Path | None = None
    logging_level: str = "INFO"
    collections: list[dict] = field(default_factory=lambda: [{"slug":"stephen-tong","name":"Stephen Tong","source_prefix":"ST"}])
    approved_sources: list[dict] = field(default_factory=list)
    chunking: dict = field(default_factory=dict)

    def __post_init__(self):
        self.data_root = Path(self.data_root)
        self.database_path = Path(self.database_path or self.data_root / "catalog" / "ptai_catalog.db")

def load_settings(path: str | Path | None = None) -> Settings:
    path = Path(path or os.getenv("PTAI_CONFIG", "config.yml"))
    values = yaml.safe_load(path.read_text()) if path.exists() else {}
    if os.getenv("PTAI_DATA_ROOT"):
        values["data_root"] = os.environ["PTAI_DATA_ROOT"]
    return Settings(**(values or {}))