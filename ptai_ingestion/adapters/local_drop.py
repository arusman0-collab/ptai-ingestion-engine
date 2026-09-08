from pathlib import Path
from .base import Adapter
class LocalDropAdapter(Adapter):
    supported={".txt",".html",".htm",".pdf"}
    def __init__(self, path: str | Path, collection="stephen-tong", rights_status="permitted_archive"):
        self.path=Path(path); self.collection=collection; self.rights_status=rights_status
    def discover(self):
        if not self.path.exists(): return []
        return [{"local_path":str(p.resolve()),"title":p.stem,"url":None,"normalized_url":f"file://{p.resolve()}","source_type":p.suffix[1:].lower(),"collection_slug":self.collection,"rights_status":self.rights_status,"adapter":"local_drop","metadata":{"original_filename":p.name}} for p in self.path.iterdir() if p.is_file() and p.suffix.lower() in self.supported]
    def inspect(self,candidate): return candidate
    def acquire(self,candidate): return Path(candidate["local_path"])
    def extract_metadata(self,candidate): return candidate.get("metadata",{})