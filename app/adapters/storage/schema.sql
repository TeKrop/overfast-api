-- OverFast API v4 - SQLite Persistent Storage Schema
-- This file defines the three core tables for the persistent storage layer

-- Static data: heroes, maps, gamemodes, roles, hero_stats
-- Key format examples:
--   - "heroes:en-us"
--   - "maps:en-us"
--   - "hero_stats:pc:competitive:europe:all-maps:all"
CREATE TABLE IF NOT EXISTS static_data (
    key TEXT PRIMARY KEY,
    data_type TEXT NOT NULL,  -- 'json' or 'html'
    data_compressed BLOB NOT NULL,  -- zstd compressed data
    created_at INTEGER NOT NULL,  -- Unix timestamp (first write)
    updated_at INTEGER NOT NULL,  -- Unix timestamp (last write)
    schema_version INTEGER DEFAULT 1
);

-- Player profiles: full career data from Blizzard
-- Key: player_id (BattleTag or Blizzard ID)
CREATE TABLE IF NOT EXISTS player_profiles (
    player_id TEXT PRIMARY KEY,
    blizzard_id TEXT,  -- Blizzard ID (for Battle Tag → ID mapping)
    html_compressed BLOB NOT NULL,  -- zstd compressed HTML
    summary_json TEXT,  -- Full player summary from search endpoint (JSON)
    last_updated_blizzard INTEGER,  -- Blizzard's last-modified timestamp
    created_at INTEGER NOT NULL,  -- Unix timestamp (first write)
    updated_at INTEGER NOT NULL,  -- Unix timestamp (last write)
    schema_version INTEGER DEFAULT 1,
    UNIQUE(blizzard_id)
);

-- Player status: unknown players with exponential backoff
-- Tracks players that don't exist on Blizzard
CREATE TABLE IF NOT EXISTS player_status (
    player_id TEXT PRIMARY KEY,
    check_count INTEGER NOT NULL DEFAULT 1,  -- Number of failed checks
    last_checked_at INTEGER NOT NULL,  -- Unix timestamp
    retry_after INTEGER NOT NULL  -- Seconds to wait before next check
);

-- Note: Indexes removed as they were not used by any queries
-- PRIMARY KEY indexes are sufficient for current query patterns
-- If adding background cleanup tasks in future, consider adding:
--   - CREATE INDEX idx_static_updated ON static_data(updated_at);
--   - CREATE INDEX idx_player_updated ON player_profiles(updated_at);
--   - CREATE INDEX idx_player_retry ON player_status(last_checked_at, retry_after);
