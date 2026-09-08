from __future__ import annotations
from pathlib import Path
import shutil, re
import json
from .hashing import sha256_file

class ArchiveStorage:
    def __init__(self, root: Path):
        self.root = Path(root)
        for name in ("original", "processed", "metadata", "catalog", "drop"): (self.root/name).mkdir(parents=True, exist_ok=True)
    @staticmethod
    def safe_name(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name)
    def preserve_original(self, source: Path, source_id: str) -> tuple[Path, str]:
        digest = sha256_file(source); folder = self.root/"original"/source_id
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{digest[:16]}_{self.safe_name(source.name)}"
        if target.exists():
            if sha256_file(target) != digest: raise FileExistsError(f"immutable original collision: {target}")
        else: shutil.copy2(source, target)
        return target, digest
    def processed_path(self, source_id: str) -> Path:
        path=self.root/"processed"/f"{source_id}.txt"; path.parent.mkdir(parents=True,exist_ok=True); return path
    def write_metadata(self, source_id: str, values: dict) -> Path:
        path=self.root/"metadata"/f"{source_id}.json"
        # Metadata is a derived processing record; it can be rebuilt without changing the original.
        path.write_text(json.dumps(values, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return path