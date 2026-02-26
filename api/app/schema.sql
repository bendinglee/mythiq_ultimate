PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS pattern_variants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pattern_id TEXT NOT NULL,
  variant TEXT NOT NULL,
  system_prompt TEXT NOT NULL,
  prefix TEXT NOT NULL,
  created_ts INTEGER NOT NULL,
  updated_ts INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pattern_variants_pattern
  ON pattern_variants(pattern_id);

CREATE INDEX IF NOT EXISTS idx_pattern_variants_pattern_variant
  ON pattern_variants(pattern_id, variant);

-- outcomes (reward events)
CREATE TABLE IF NOT EXISTS outcomes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  feature TEXT NOT NULL,
  key_name TEXT NOT NULL,

  reward REAL NOT NULL,
  meta_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_outcomes_ts ON outcomes(ts);
CREATE INDEX IF NOT EXISTS idx_outcomes_feature_key_name ON outcomes(feature, key_name);

-- generations (model outputs / artifacts)
CREATE TABLE IF NOT EXISTS generations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  feature TEXT NOT NULL,
  key_name TEXT NOT NULL,

  prompt TEXT NOT NULL,
  output TEXT NOT NULL,
  meta_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_generations_ts ON generations(ts);
CREATE INDEX IF NOT EXISTS idx_generations_feature_key_name ON generations(feature, key_name);
-- enforce uniqueness for upserts
CREATE UNIQUE INDEX IF NOT EXISTS uniq_pattern_variants_pattern_variant
  ON pattern_variants(pattern_id, variant);

-- A/B decision cache (computed winner + vote counts per group)
CREATE TABLE IF NOT EXISTS ab_decisions (
  ab_group TEXT PRIMARY KEY,
  winner TEXT,
  votes_a INTEGER NOT NULL DEFAULT 0,
  votes_b INTEGER NOT NULL DEFAULT 0,
  updated_ts INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ab_decisions_updated_ts ON ab_decisions(updated_ts);

-- A/B voting (one row per vote; optional voter_id for idempotency)
CREATE TABLE IF NOT EXISTS ab_votes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  ab_group TEXT NOT NULL,
  vote TEXT NOT NULL,           -- 'A' or 'B'
  user_rating REAL,             -- optional rating signal
  voter_id TEXT                 -- optional idempotency key
);

-- Prevent duplicate votes from the same voter_id within the same ab_group
CREATE UNIQUE INDEX IF NOT EXISTS idx_ab_votes_group_voter ON ab_votes(ab_group, voter_id);

CREATE INDEX IF NOT EXISTS idx_ab_votes_group_ts ON ab_votes(ab_group, ts);
CREATE INDEX IF NOT EXISTS idx_ab_votes_ts ON ab_votes(ts);
