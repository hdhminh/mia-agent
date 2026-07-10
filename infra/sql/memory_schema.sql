CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS mia_memory_items (
  id BIGSERIAL PRIMARY KEY,
  chat_id TEXT NOT NULL,
  fingerprint TEXT NOT NULL UNIQUE,
  memory_type TEXT NOT NULL DEFAULT 'general',
  title TEXT NOT NULL DEFAULT '',
  content TEXT NOT NULL,
  source_text TEXT NOT NULL DEFAULT '',
  tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  importance INTEGER NOT NULL DEFAULT 3,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.75,
  source TEXT NOT NULL DEFAULT 'mia_langchain_core',
  last_used_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  superseded_by BIGINT REFERENCES mia_memory_items(id) ON DELETE SET NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE mia_memory_items ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION NOT NULL DEFAULT 0.75;
ALTER TABLE mia_memory_items ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'mia_langchain_core';
ALTER TABLE mia_memory_items ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;
ALTER TABLE mia_memory_items ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE mia_memory_items ADD COLUMN IF NOT EXISTS superseded_by BIGINT REFERENCES mia_memory_items(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS mia_memory_chunks (
  id BIGSERIAL PRIMARY KEY,
  item_id BIGINT NOT NULL REFERENCES mia_memory_items(id) ON DELETE CASCADE,
  chat_id TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  embedding VECTOR(384) NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mia_memory_items_chat_updated
  ON mia_memory_items (chat_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_mia_memory_items_chat_type
  ON mia_memory_items (chat_id, memory_type, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_mia_memory_items_tags
  ON mia_memory_items USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_mia_memory_items_active_expiry
  ON mia_memory_items (chat_id, is_active, expires_at);

CREATE INDEX IF NOT EXISTS idx_mia_memory_chunks_chat_created
  ON mia_memory_chunks (chat_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mia_memory_chunks_text_trgm
  ON mia_memory_chunks USING GIN (chunk_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_mia_memory_chunks_embedding_hnsw
  ON mia_memory_chunks USING HNSW (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS mia_learning_events (
  id BIGSERIAL PRIMARY KEY,
  chat_id TEXT NOT NULL,
  request_id TEXT NOT NULL,
  thread_id TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT 'chat',
  scope TEXT NOT NULL DEFAULT 'general',
  topic TEXT NOT NULL DEFAULT '',
  user_text TEXT NOT NULL DEFAULT '',
  final_text TEXT NOT NULL DEFAULT '',
  tools_called TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  issue_type TEXT NOT NULL DEFAULT '',
  severity INTEGER NOT NULL DEFAULT 0,
  model TEXT NOT NULL DEFAULT '',
  prompt_cache_key TEXT NOT NULL DEFAULT '',
  cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
  cached_tokens INTEGER NOT NULL DEFAULT 0,
  prompt_tokens INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  total_tokens INTEGER NOT NULL DEFAULT 0,
  trace JSONB NOT NULL DEFAULT '{}'::JSONB,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  notes TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mia_learning_insights (
  id BIGSERIAL PRIMARY KEY,
  scope TEXT NOT NULL DEFAULT 'general',
  topic TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  prompt_hint TEXT NOT NULL DEFAULT '',
  memory_hint TEXT NOT NULL DEFAULT '',
  support_count INTEGER NOT NULL DEFAULT 0,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  usage_count INTEGER NOT NULL DEFAULT 0,
  last_used_at TIMESTAMPTZ,
  promoted_at TIMESTAMPTZ,
  decay_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  examples JSONB NOT NULL DEFAULT '[]'::JSONB,
  source_digest TEXT NOT NULL UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE mia_learning_insights ADD COLUMN IF NOT EXISTS usage_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE mia_learning_insights ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;
ALTER TABLE mia_learning_insights ADD COLUMN IF NOT EXISTS promoted_at TIMESTAMPTZ;
ALTER TABLE mia_learning_insights ADD COLUMN IF NOT EXISTS decay_score DOUBLE PRECISION NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS mia_learning_feedbacks (
  id BIGSERIAL PRIMARY KEY,
  chat_id TEXT NOT NULL,
  request_id TEXT NOT NULL,
  thread_id TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT 'chat',
  scope TEXT NOT NULL DEFAULT 'general',
  topic TEXT NOT NULL DEFAULT '',
  verdict TEXT NOT NULL DEFAULT '',
  rating INTEGER NOT NULL DEFAULT 0,
  comment TEXT NOT NULL DEFAULT '',
  correction_text TEXT NOT NULL DEFAULT '',
  current_text TEXT NOT NULL DEFAULT '',
  trace JSONB NOT NULL DEFAULT '{}'::JSONB,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mia_learning_events_chat_created
  ON mia_learning_events (chat_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mia_learning_events_scope_created
  ON mia_learning_events (scope, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mia_learning_events_issue
  ON mia_learning_events (issue_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mia_learning_insights_scope_active
  ON mia_learning_insights (scope, is_active, confidence DESC, support_count DESC, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_mia_learning_insights_usage
  ON mia_learning_insights (is_active, usage_count DESC, last_used_at DESC);

CREATE INDEX IF NOT EXISTS idx_mia_learning_feedbacks_chat_created
  ON mia_learning_feedbacks (chat_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mia_learning_feedbacks_scope_created
  ON mia_learning_feedbacks (scope, created_at DESC);

CREATE TABLE IF NOT EXISTS mia_pending_actions (
  id BIGSERIAL PRIMARY KEY,
  chat_id TEXT NOT NULL,
  user_id TEXT NOT NULL DEFAULT '',
  request_id TEXT NOT NULL,
  tool_name TEXT NOT NULL DEFAULT '',
  gateway_name TEXT NOT NULL DEFAULT '',
  args JSONB NOT NULL DEFAULT '{}'::JSONB,
  summary TEXT NOT NULL DEFAULT '',
  reason TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',
  error_text TEXT NOT NULL DEFAULT '',
  result_text TEXT NOT NULL DEFAULT '',
  claimed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '15 minutes')
);

ALTER TABLE mia_pending_actions ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT '';
ALTER TABLE mia_pending_actions ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_mia_pending_actions_chat_status
  ON mia_pending_actions (chat_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mia_pending_actions_expires
  ON mia_pending_actions (status, expires_at);

CREATE INDEX IF NOT EXISTS idx_mia_pending_actions_owner_status
  ON mia_pending_actions (chat_id, user_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS mia_execution_journal (
  id BIGSERIAL PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  request_id TEXT NOT NULL,
  chat_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  args_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'running',
  result JSONB NOT NULL DEFAULT '{}'::JSONB,
  error_text TEXT NOT NULL DEFAULT '',
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '30 days')
);

CREATE INDEX IF NOT EXISTS idx_mia_execution_journal_owner
  ON mia_execution_journal (user_id, started_at DESC);

CREATE TABLE IF NOT EXISTS mia_skill_runs (
  id BIGSERIAL PRIMARY KEY,
  skill_name TEXT NOT NULL,
  request_id TEXT NOT NULL UNIQUE,
  chat_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'running',
  current_step INTEGER NOT NULL DEFAULT 0,
  completed_steps JSONB NOT NULL DEFAULT '[]'::JSONB,
  state JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_mia_skill_runs_owner
  ON mia_skill_runs (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS mia_automations (
  id BIGSERIAL PRIMARY KEY,
  chat_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  schedule TEXT NOT NULL,
  skill_name TEXT NOT NULL,
  input_text TEXT NOT NULL DEFAULT '',
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  next_run_at TIMESTAMPTZ,
  last_run_at TIMESTAMPTZ,
  lease_until TIMESTAMPTZ,
  last_error TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE mia_automations ADD COLUMN IF NOT EXISTS lease_until TIMESTAMPTZ;
ALTER TABLE mia_automations ADD COLUMN IF NOT EXISTS last_error TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_mia_automations_due
  ON mia_automations (enabled, next_run_at);

CREATE INDEX IF NOT EXISTS idx_mia_automations_owner
  ON mia_automations (user_id, updated_at DESC);
