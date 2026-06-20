CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DROP TABLE IF EXISTS mia_memory_chunks CASCADE;
DROP TABLE IF EXISTS mia_memory_items CASCADE;
DROP TABLE IF EXISTS mia_facts CASCADE;
DROP TABLE IF EXISTS mia_episodes CASCADE;

CREATE TABLE mia_memory_items (
  id BIGSERIAL PRIMARY KEY,
  chat_id TEXT NOT NULL,
  fingerprint TEXT NOT NULL UNIQUE,
  memory_type TEXT NOT NULL DEFAULT 'general',
  title TEXT NOT NULL DEFAULT '',
  content TEXT NOT NULL,
  source_text TEXT NOT NULL DEFAULT '',
  tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  importance INTEGER NOT NULL DEFAULT 3,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE mia_memory_chunks (
  id BIGSERIAL PRIMARY KEY,
  item_id BIGINT NOT NULL REFERENCES mia_memory_items(id) ON DELETE CASCADE,
  chat_id TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  embedding VECTOR(384) NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_mia_memory_items_chat_updated
  ON mia_memory_items (chat_id, updated_at DESC);

CREATE INDEX idx_mia_memory_items_chat_type
  ON mia_memory_items (chat_id, memory_type, updated_at DESC);

CREATE INDEX idx_mia_memory_items_tags
  ON mia_memory_items USING GIN (tags);

CREATE INDEX idx_mia_memory_chunks_chat_created
  ON mia_memory_chunks (chat_id, created_at DESC);

CREATE INDEX idx_mia_memory_chunks_text_trgm
  ON mia_memory_chunks USING GIN (chunk_text gin_trgm_ops);

CREATE INDEX idx_mia_memory_chunks_embedding_hnsw
  ON mia_memory_chunks USING HNSW (embedding vector_cosine_ops);
