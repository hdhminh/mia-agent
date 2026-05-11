CREATE TABLE IF NOT EXISTS short_links (
  id TEXT PRIMARY KEY,
  long_url TEXT NOT NULL,
  short_url TEXT NOT NULL,
  host TEXT,
  clicks INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_clicked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_short_links_host ON short_links(host);
CREATE INDEX IF NOT EXISTS idx_short_links_created_at ON short_links(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_short_links_expires_at ON short_links(expires_at);
