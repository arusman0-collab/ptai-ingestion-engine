CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS collections (id INTEGER PRIMARY KEY, slug TEXT UNIQUE NOT NULL, name TEXT NOT NULL, source_prefix TEXT UNIQUE NOT NULL, next_source_number INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS works (id INTEGER PRIMARY KEY, collection_id INTEGER NOT NULL REFERENCES collections(id), title TEXT, author TEXT, date TEXT, date_precision TEXT, series_title TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS sources (
 id INTEGER PRIMARY KEY, source_id TEXT UNIQUE NOT NULL, collection_id INTEGER NOT NULL REFERENCES collections(id), work_id INTEGER REFERENCES works(id),
 title TEXT, speaker TEXT, author TEXT, date TEXT, date_precision TEXT, series_title TEXT, episode_number TEXT, language TEXT,
 source_type TEXT, publisher TEXT, platform TEXT, canonical_url TEXT, original_url TEXT, discovery_url TEXT, discovery_date TEXT,
 source_level TEXT, rights_status TEXT NOT NULL DEFAULT 'unknown', archive_status TEXT NOT NULL DEFAULT 'new',
 local_original_path TEXT, processed_path TEXT, metadata_path TEXT, sha256 TEXT, mime_type TEXT, file_size INTEGER,
 transcript_status TEXT DEFAULT 'unknown', transcript_provenance TEXT, verified_by_speaker INTEGER DEFAULT 0, topics TEXT,
 bible_passages TEXT, people_mentioned TEXT, works_mentioned TEXT, source_citations TEXT, quality_score REAL,
 review_status TEXT, error_log TEXT, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS manifestations (id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES sources(id), kind TEXT NOT NULL, language TEXT, original_filename TEXT, extraction_method TEXT, page_count INTEGER, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS discovery_queue (id INTEGER PRIMARY KEY, adapter TEXT NOT NULL, platform TEXT, title TEXT, url TEXT, normalized_url TEXT UNIQUE, local_path TEXT, possible_author TEXT, source_type TEXT, collection_slug TEXT, rights_status TEXT NOT NULL DEFAULT 'unknown', status TEXT NOT NULL DEFAULT 'new', metadata_json TEXT, discovered_at TEXT NOT NULL, source_id TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS processing_events (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, source_id TEXT, manifestation_id INTEGER, pipeline_stage TEXT NOT NULL, previous_state TEXT, new_state TEXT, status TEXT NOT NULL, elapsed_ms INTEGER, software_version TEXT, model_version TEXT, message TEXT, error TEXT, processing_run_id TEXT);
CREATE TABLE IF NOT EXISTS rights_records (id INTEGER PRIMARY KEY, source_id INTEGER REFERENCES sources(id), status TEXT NOT NULL, basis TEXT, recorded_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS people (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL); CREATE TABLE IF NOT EXISTS source_people (source_id INTEGER, person_id INTEGER, role TEXT);
CREATE TABLE IF NOT EXISTS works_cited (id INTEGER PRIMARY KEY, citation TEXT UNIQUE); CREATE TABLE IF NOT EXISTS source_works_cited (source_id INTEGER, work_id INTEGER);
CREATE TABLE IF NOT EXISTS bible_references (id INTEGER PRIMARY KEY, reference TEXT UNIQUE); CREATE TABLE IF NOT EXISTS source_bible_references (source_id INTEGER, bible_reference_id INTEGER);
CREATE TABLE IF NOT EXISTS processing_runs (id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, completed_at TEXT, command TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS system_versions (id INTEGER PRIMARY KEY, component TEXT NOT NULL, version TEXT NOT NULL, recorded_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_sources_sha ON sources(sha256); CREATE INDEX IF NOT EXISTS ix_sources_status ON sources(archive_status); CREATE INDEX IF NOT EXISTS ix_events_source ON processing_events(source_id);