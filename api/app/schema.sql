PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS pattern_variants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pattern_id TEXT NOT NULL,
  variant TEXT NOT NULL,
  system_prompt TEXT NOT NULL,
  prefix TEXT NOT NULL,
  created_ts INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pattern_variants_pattern
  ON pattern_variants(pattern_id);

CREATE INDEX IF NOT EXISTS idx_pattern_variants_pattern_variant
  ON pattern_variants(pattern_id, variant);
