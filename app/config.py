"""Project constants module"""

import tomllib
from functools import cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


@cache
def get_app_version() -> str:
    with Path(f"{Path.cwd()}/pyproject.toml").open(mode="rb") as project_file:
        project_data = tomllib.load(project_file)
    return project_data["project"]["version"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ############
    # APPLICATION SETTINGS
    ############

    # Application volume path for container (logs, dotenv settings, etc.)
    # If not specified, temporary folder will be used
    app_volume_path: str = ""

    # Application port
    app_port: int = 80

    # Application version, retrieved from pyproject.toml. It should never be
    # overriden in dotenv. Only used in OpenAPI spec and request headers.
    app_version: str = get_app_version()

    # Base URL of the application
    # Used in some endpoints for exposing internal and static links
    app_base_url: str = "https://overfast-api.tekrop.fr"

    # Log level for Loguru
    log_level: str = "info"

    # Optional, status page URL if you have any to provide
    status_page_url: str | None = None

    # Profiler to use for debug purposes, disabled by default
    profiler: str | None = None

    # Route path to display as new on the documentation
    new_route_path: str | None = None

    # Enable Prometheus metrics collection and /metrics endpoint
    prometheus_enabled: bool = False

    ############
    # PERSISTENT STORAGE CONFIGURATION
    ############

    # SQLite database path for persistent storage
    # Use ":memory:" for in-memory database (testing/ephemeral deployments)
    storage_path: str = "data/overfast.db"

    # SQLite connection pool size — each connection runs in its own thread,
    # enabling parallel reads under WAL mode. Writes still serialize at the
    # SQLite level. Use 1 for :memory: (shared only within one connection).
    sqlite_pool_size: int = 5

    # SQLite memory-mapped I/O size in bytes (optional performance tuning)
    sqlite_mmap_size: int = 0

    # SQLite page cache size per connection in kibibytes (negative = KiB, positive = pages)
    # -4000 = 4 MB/connection; keeps player_status table and indexes hot in every connection
    sqlite_cache_size: int = -4000

    # SQLite WAL auto-checkpoint threshold in pages (4 KB/page by default)
    # 500 pages = ~2 MB WAL; smaller WAL reduces read scan overhead
    sqlite_wal_autocheckpoint: int = 500

    # Unknown player exponential backoff configuration
    unknown_player_initial_retry: int = 600  # 10 minutes (first check)
    unknown_player_retry_multiplier: int = 3  # retry_after *= 3 each check
    unknown_player_max_retry: int = 21600  # 6 hours cap

    ############
    # RATE LIMITING
    ############

    # Name for the response header which will contain
    # the number of seconds before retrying if being rate limited
    retry_after_header: str = "Retry-After"

    # Valkey key for Blizzard rate limit storage
    blizzard_rate_limit_key: str = "blizzard-rate-limit"

    # Number of seconds before the user is authorized to make calls to Blizzard again
    blizzard_rate_limit_retry_after: int = 5

    # Global rate limit of requests per second per ip to apply on the API
    rate_limit_per_second_per_ip: int = 30

    # Global burst value to apply on rate limit before rejecting requests
    rate_limit_per_ip_burst: int = 5

    # Global maximum number of connection/simultaneous requests per ip
    max_connections_per_ip: int = 10

    ############
    # VALKEY CONFIGURATION
    ############

    # Valkey server host
    valkey_host: str = "127.0.0.1"

    # Valkey server port
    valkey_port: int = 6379

    # Valkey memory limit
    valkey_memory_limit: str = "1gb"

    ############
    # CACHE CONFIGURATION
    ############

    # Name for the response header which will contain
    # the API Cache TTL when calling the API
    cache_ttl_header: str = "X-Cache-TTL"

    # Prefix for keys in API Cache with entire payload (Valkey).
    # Used by nginx as main API cache.
    api_cache_key_prefix: str = "api-cache"

    # Prefix for keys in Player Cache (Valkey). Used by player classes
    # in order to avoid parsing data which has already been parsed.
    player_cache_key_prefix: str = "player-cache"

    # Cache TTL for Player Cache. Whenever a key is accessed, its TTL is reset.
    # It will only expires if not accessed during TTL time.
    player_cache_timeout: int = 259200

    # Cache TTL for heroes list data (seconds)
    heroes_path_cache_timeout: int = 86400

    # Cache TTL for specific hero data (seconds)
    hero_path_cache_timeout: int = 86400

    # Cache TTL for local CSV-based data : heroes stats, gamemodes and maps
    csv_cache_timeout: int = 86400

    # Cache TTL for career pages data (seconds)
    career_path_cache_timeout: int = 3600

    # Cache TTL for search account data (seconds)
    search_account_path_cache_timeout: int = 600

    # Cache TTL for hero stats data (seconds)
    hero_stats_cache_timeout: int = 3600

    ############
    # UNKNOWN PLAYERS SYSTEM
    ############

    # Indicate if unknown players cache is enabled or not
    unknown_players_cache_enabled: bool = True

    # Cache key for unknown players cache in Redis.
    unknown_players_cache_key_prefix: str = "unknown-players-cache"

    # Cache TTL for not unknown players (seconds)
    unknown_players_cache_timeout: int = 3600

    ############
    # BLIZZARD
    ############

    # Blizzard base url for Overwatch website
    blizzard_host: str = "https://overwatch.blizzard.com"

    # Blizzard home page with some details
    home_path: str = "/"

    # Route for Overwatch heroes pages (locale can be specified by API users)
    heroes_path: str = "/heroes/"

    # Route for players career pages
    career_path: str = "/en-us/career"

    # Route for searching Overwatch accounts by name
    search_account_path: str = "/en-us/search/account-by-name"

    # Route for retrieving usage statistics about Overwatch heroes
    hero_stats_path: str = "/en-us/rates/data/"

    ############
    # CRITICAL ERROR DISCORD WEBHOOK
    ############

    # Enable Discord Webhook for critical errors or not
    discord_webhook_enabled: bool = False

    # Discord Webhook URL
    discord_webhook_url: str = ""

    # Error message to be displayed to API users
    internal_server_error_message: str = (
        "An internal server error occurred during the process. The developer "
        "received a notification, but don't hesitate to create a GitHub "
        "issue if you want any news concerning the bug resolution : "
        "https://github.com/TeKrop/overfast-api/issues"
    )

    # Enable Discord message when rate limiting is being applied
    discord_message_on_rate_limit: bool = False

    ############
    # SENTRY CONFIGURATION
    ############

    # Sentry DSN
    sentry_dsn: str = ""

    ############
    # LOCAL
    ############

    # Root path for test fixtures, used to update test data when Blizzard pages are updated
    # It should never be overriden in dotenv.
    test_fixtures_root_path: str = f"{Path.cwd()}/tests/fixtures"

    # Root path for Loguru access logs. It should never be overriden in dotenv.
    logs_root_path: str = f"{Path.cwd()}/logs"


@cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
