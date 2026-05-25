CREATE TABLE IF NOT EXISTS feeds (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  site_url TEXT NOT NULL DEFAULT '',
  feed_url TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT '',
  language TEXT,
  last_fetched_at TEXT,
  etag TEXT,
  last_modified TEXT,
  status TEXT NOT NULL DEFAULT 'idle',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feeds_feed_url ON feeds(feed_url);

CREATE TABLE IF NOT EXISTS articles (
  id TEXT PRIMARY KEY,
  feed_id TEXT NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  author TEXT NOT NULL DEFAULT '',
  url TEXT NOT NULL,
  guid TEXT,
  published_at TEXT,
  fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_read INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
  is_starred INTEGER NOT NULL DEFAULT 0 CHECK (is_starred IN (0, 1)),
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(feed_id, guid),
  UNIQUE(feed_id, url)
);

CREATE INDEX IF NOT EXISTS idx_articles_feed_published ON articles(feed_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_read ON articles(is_read);
CREATE INDEX IF NOT EXISTS idx_articles_starred ON articles(is_starred);

CREATE TABLE IF NOT EXISTS article_content (
  article_id TEXT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
  raw_html TEXT NOT NULL DEFAULT '',
  cleaned_html TEXT NOT NULL DEFAULT '',
  cleaned_markdown TEXT NOT NULL DEFAULT '',
  plain_text TEXT NOT NULL DEFAULT '',
  content_hash TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id TEXT PRIMARY KEY,
  article_id TEXT REFERENCES articles(id) ON DELETE CASCADE,
  agent_type TEXT NOT NULL CHECK (agent_type IN ('summary', 'translation', 'tag')),
  status TEXT NOT NULL,
  provider TEXT NOT NULL DEFAULT '',
  model TEXT NOT NULL DEFAULT '',
  input_hash TEXT,
  target_lang TEXT,
  output_text TEXT,
  output_json TEXT,
  error_message TEXT,
  prompt_tokens INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  total_tokens INTEGER NOT NULL DEFAULT 0,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_article_type ON agent_runs(article_id, agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);

CREATE TABLE IF NOT EXISTS agent_steps (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  step_index INTEGER NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  input_json TEXT,
  output_json TEXT,
  error_message TEXT,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  UNIQUE(run_id, step_index)
);

CREATE TABLE IF NOT EXISTS provider_settings (
  provider TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
  base_url TEXT,
  default_model TEXT,
  api_key_ref TEXT,
  settings_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_config (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
