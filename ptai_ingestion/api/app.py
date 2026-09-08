from fastapi import FastAPI, HTTPException
from ..config import load_settings
from ..catalog import Catalog

def create_app(config_path=None):
 settings=load_settings(config_path); catalog=Catalog(settings.database_path); catalog.migrate(); catalog.ensure_collections(settings.collections)
 app=FastAPI(title="PT-AI Ingestion Operator API",version="0.1.0")
 @app.get("/api/status")
 def status(): return {"counts":catalog.counts(),"queue":catalog.conn.execute("SELECT status,count(*) n FROM discovery_queue GROUP BY status").fetchall()}
 @app.get("/api/sources")
 def sources(status: str|None=None):
  query="SELECT source_id,title,archive_status,rights_status,source_type,updated_at FROM sources"; args=()
  if status: query+=" WHERE archive_status=?"; args=(status,)
  return [dict(r) for r in catalog.conn.execute(query,args).fetchall()]
 @app.get("/api/sources/{source_id}")
 def source(source_id:str):
  record=catalog.source(source_id)
  if not record: raise HTTPException(404,"source not found")
  events=catalog.conn.execute("SELECT * FROM processing_events WHERE source_id=? ORDER BY id",(source_id,)).fetchall()
  return {"source":dict(record),"events":[dict(x) for x in events]}
 @app.get("/api/queue")
 def queue(status:str|None=None):
  sql="SELECT * FROM discovery_queue"+(" WHERE status=?" if status else ""); return [dict(r) for r in catalog.conn.execute(sql,(status,) if status else ()).fetchall()]
 @app.get("/api/review")
 def review(): return [dict(r) for r in catalog.conn.execute("SELECT * FROM sources WHERE archive_status IN ('needs_review','rights_hold','extraction_failed','indexing_failed')").fetchall()]
 return app

app=create_app()