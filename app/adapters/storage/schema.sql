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
-- Key: player_id (ALWAYS Blizzard ID as of Phase 3.5B)
-- Note: battletag and name are optional metadata, can be NULL
CREATE TABLE IF NOT EXISTS player_profiles (
    player_id TEXT PRIMARY KEY,  -- Blizzard ID (canonical identifier)
    battletag TEXT,  -- Full BattleTag from user input (e.g., "TeKrop-2217"), can be NULL
    name TEXT,  -- Display name only (e.g., "TeKrop"), extracted from HTML or summary
    html_compressed BLOB NOT NULL,  -- zstd compressed HTML
    summary_json TEXT,  -- Full player summary from search endpoint (JSON)
    last_updated_blizzard INTEGER,  -- Blizzard's last-modified timestamp
    created_at INTEGER NOT NULL,  -- Unix timestamp (first write)
    updated_at INTEGER NOT NULL,  -- Unix timestamp (last write)
    schema_version INTEGER DEFAULT 1
);

-- Player status: unknown players with exponential backoff
-- Tracks players that don't exist on Blizzard
-- Key: player_id (ALWAYS Blizzard ID as of Phase 3.5B)
-- Also stores battletag if available to enable early rejection of BattleTag requests
CREATE TABLE IF NOT EXISTS player_status (
    player_id TEXT PRIMARY KEY,  -- Blizzard ID (canonical identifier)
    battletag TEXT,  -- BattleTag if available (enables early check on BattleTag requests)
    check_count INTEGER NOT NULL DEFAULT 1,  -- Number of failed checks
    last_checked_at INTEGER NOT NULL,  -- Unix timestamp
    retry_after INTEGER NOT NULL  -- Seconds to wait before next check
);

-- Index to enable fast lookups by BattleTag
CREATE INDEX IF NOT EXISTS idx_player_status_battletag ON player_status(battletag);

-- Note: Indexes removed as they were not used by any queries
-- PRIMARY KEY indexes are sufficient for current query patterns
-- If adding background cleanup tasks in future, consider adding:
--   - CREATE INDEX idx_static_updated ON static_data(updated_at);
--   - CREATE INDEX idx_player_updated ON player_profiles(updated_at);
--   - CREATE INDEX idx_player_retry ON player_status(last_checked_at, retry_after);
