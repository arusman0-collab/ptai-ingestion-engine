CREATE TABLE IF NOT EXISTS source_index_versions (
 source_id TEXT PRIMARY KEY REFERENCES sources(source_id),
 chunking_version TEXT NOT NULL, embedding_model TEXT NOT NULL,
 embedding_dimensions INTEGER NOT NULL, indexed_at TEXT NOT NULL
);