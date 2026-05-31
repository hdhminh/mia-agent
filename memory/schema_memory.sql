CREATE TABLE IF NOT EXISTS mia_facts (
  id SERIAL PRIMARY KEY,
  chat_id TEXT NOT NULL,
  fingerprint TEXT NOT NULL UNIQUE,
  fact_text TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'general',
  tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  source_text TEXT NOT NULL DEFAULT '',
  confidence NUMERIC(3,2) NOT NULL DEFAULT 0.80,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mia_facts_chat_id_updated
ON mia_facts (chat_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS mia_episodes (
  id SERIAL PRIMARY KEY,
  chat_id TEXT NOT NULL,
  episode_summary TEXT NOT NULL,
  topic TEXT NOT NULL DEFAULT 'general',
  tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  source_text TEXT NOT NULL DEFAULT '',
  episode_date DATE NOT NULL DEFAULT CURRENT_DATE,
  importance INTEGER NOT NULL DEFAULT 3,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mia_episodes_chat_id_updated
ON mia_episodes (chat_id, updated_at DESC);
