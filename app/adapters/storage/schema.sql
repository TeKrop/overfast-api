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

-- Index to enable fast BattleTag lookups in player_profiles
-- Used by get_player_id_by_battletag() for redirect optimization (Phase 3.5B)
CREATE INDEX IF NOT EXISTS idx_player_profiles_battletag ON player_profiles(battletag);

-- Index on updated_at for data freshness queries (metrics)
-- Used by get_stats() to efficiently calculate p50/p90/p99 age distribution
CREATE INDEX IF NOT EXISTS idx_player_profiles_updated ON player_profiles(updated_at);

-- Note: Indexes removed as they were not used by any queries
-- PRIMARY KEY indexes are sufficient for current query patterns
-- If adding background cleanup tasks in future, consider adding:
--   - CREATE INDEX idx_static_updated ON static_data(updated_at);
--   - CREATE INDEX idx_player_updated ON player_profiles(updated_at);
