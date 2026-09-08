from __future__ import annotations
import json
from pathlib import Path
import typer
from .config import load_settings
from .catalog import Catalog
from .storage import ArchiveStorage
from .pipeline import Pipeline
from .adapters.local_drop import LocalDropAdapter
from .hashing import sha256_file
app=typer.Typer(help="PT-AI provenance-first ingestion engine")
def services(config=None):
 s=load_settings(config); c=Catalog(s.database_path); c.migrate(); c.ensure_collections(s.collections); return s,c,Pipeline(c,ArchiveStorage(s.data_root))
@app.command()
def discover(config: str|None=None, adapter: str="local_drop", dry_run:bool=False):
 s,c,p=services(config)
 if adapter!="local_drop": raise typer.BadParameter("Phase 1 supports only local_drop")
 entries=[x for x in s.approved_sources if x.get("adapter","local_drop")==adapter]
 for entry in entries:
  a=LocalDropAdapter(entry["path"],entry.get("collection","stephen-tong"),entry.get("rights_status","permitted_archive"))
  if dry_run: typer.echo(f"{len(a.discover())} candidates"); continue
  p.discover(a)
 typer.echo("discovery complete")
@app.command()
def queue(config: str|None=None, json_output:bool=typer.Option(False,"--json")):
 _,c,_=services(config); rows=[dict(x) for x in c.conn.execute("SELECT * FROM discovery_queue ORDER BY id").fetchall()]; typer.echo(json.dumps(rows,default=str) if json_output else "\n".join(f"{x['id']} {x['status']} {x['title']}" for x in rows))
@app.command()
def process(queue_id: int|None=None, config: str|None=None, dry_run:bool=False):
 _,_,p=services(config)
 if dry_run: typer.echo("dry-run: no sources processed"); return
 try: p.process(queue_id)
 except ValueError as exc: raise typer.BadParameter(str(exc))
 typer.echo("processing complete")
@app.command()
def status(config: str|None=None, json_output:bool=typer.Option(False,"--json")):
 _,c,_=services(config); result={"sources":c.counts(),"queue":dict(c.conn.execute("SELECT status,count(*) FROM discovery_queue GROUP BY status").fetchall())}; typer.echo(json.dumps(result) if json_output else result)
@app.command("verify-integrity")
def verify_integrity(config: str|None=None):
 _,c,_=services(config); bad=0
 for row in c.conn.execute("SELECT source_id,local_original_path,sha256 FROM sources WHERE local_original_path IS NOT NULL"):
  try: state="OK" if Path(row["local_original_path"]).exists() and sha256_file(row["local_original_path"])==row["sha256"] else ("missing" if not Path(row["local_original_path"]).exists() else "hash mismatch")
  except OSError: state="unreadable"
  typer.echo(f"{row['source_id']}: {state}"); bad += state!="OK"
 if bad: raise typer.Exit(1)
@app.command()
def review(config: str|None=None): 
 _,c,_=services(config); [typer.echo(f"{r['source_id']} {r['archive_status']}") for r in c.conn.execute("SELECT source_id,archive_status FROM sources WHERE archive_status IN ('needs_review','rights_hold','extraction_failed')")]
@app.command()
def retry(failed: bool=typer.Option(False,"--failed"), config: str|None=None): typer.echo("Retry requires explicit human review in Phase 1; no held source was advanced.")
@app.command()
def reindex(source_id:str, config:str|None=None): typer.echo("Indexing begins in Phase 2; archive data remains authoritative.")
@app.command("rebuild-index")
def rebuild_index(config:str|None=None): typer.echo("Indexing begins in Phase 2; no vector index is managed.")