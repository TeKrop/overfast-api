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
    # PERSISTENT STORAGE CONFIGURATION (PostgreSQL)
    ############

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "overfast"
    postgres_user: str = "overfast"
    postgres_password: str = "overfast"  # noqa: S105
    postgres_pool_min_size: int = 2
    postgres_pool_max_size: int = 10

    @property
    def postgres_dsn(self) -> str:
        """Build asyncpg-compatible DSN from individual connection settings."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Maximum age of player profiles in seconds before they are considered stale.
    # Profiles with updated_at older than this threshold are removed by the periodic
    # background cleanup task to keep the database size bounded. Set to 0 to disable cleanup.
    player_profile_max_age: int = 604800  # 7 days

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

    # Global rate limit of requests per second per ip to apply on the API
    rate_limit_per_second_per_ip: int = 30

    # Global burst value to apply on rate limit before rejecting requests
    rate_limit_per_ip_burst: int = 5

    # Global maximum number of connection/simultaneous requests per ip
    max_connections_per_ip: int = 10

    ############
    # ADAPTIVE THROTTLING (AutoThrottle + AIMD)
    ############

    # Enable adaptive throttling for Blizzard requests
    throttle_enabled: bool = True

    # Initial delay between Blizzard requests (seconds)
    throttle_start_delay: float = 2.0

    # Minimum delay (floor)
    throttle_min_delay: float = 1.0

    # Maximum delay (cap)
    throttle_max_delay: float = 30.0

    # Target concurrency: 0.5 means 1 request every ~2s at steady state
    throttle_target_concurrency: float = 0.5

    # Minimum delay enforced immediately after a Blizzard 403
    throttle_penalty_delay: float = 10.0

    # Seconds after a 403 during which delay cannot decrease (recovery blocked)
    throttle_penalty_duration: int = 60

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
    # SWR STALENESS THRESHOLDS
    ############

    # Age (seconds) after which static data is considered stale and triggers
    # a background refresh while still serving the cached response.
    heroes_staleness_threshold: int = 86400  # 24 hours
    maps_staleness_threshold: int = 86400
    gamemodes_staleness_threshold: int = 86400
    roles_staleness_threshold: int = 86400

    # Age (seconds) after which a player profile is considered stale.
    player_staleness_threshold: int = 3600  # 1 hour

    # TTL (seconds) for stale responses written to Valkey API cache.
    # Short enough that background refresh (typically seconds) will overwrite it
    # with fresh data before it expires; long enough to absorb burst traffic
    # while the refresh is in-flight.
    stale_cache_timeout: int = 60

    ############
    # UNKNOWN PLAYERS SYSTEM
    ############

    # Indicate if unknown players cache is enabled or not
    unknown_players_cache_enabled: bool = True

    # Prefix for Valkey keys tracking active cooldown windows (has TTL = retry_after)
    unknown_player_cooldown_key_prefix: str = "unknown-player:cooldown"

    # Prefix for Valkey keys storing persistent check count (no TTL, survives cooldown expiry)
    unknown_player_status_key_prefix: str = "unknown-player:status"

    ############
    # BACKGROUND WORKER
    ############

    # Maximum number of concurrent worker jobs
    worker_max_concurrent_jobs: int = 10

    # Job timeout in seconds
    worker_job_timeout: int = 300

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
