"""Project constants module"""
import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseSettings


@lru_cache
def get_app_version() -> str:
    with Path(f"{Path.cwd()}/pyproject.toml").open(mode="rb") as project_file:
        project_data = tomllib.load(project_file)
    return project_data["tool"]["poetry"]["version"]


class Settings(BaseSettings):
    ############
    # APPLICATION SETTINGS
    ############

    # Application version, retrieved from pyproject.toml. It should never be
    # overriden in dotenv. Only used in OpenAPI spec and request headers.
    app_version: str = get_app_version()

    # Base URL of the application
    # Used in some endpoints for exposing internal and static links
    app_base_url: str = "https://overfast-api.tekrop.fr"

    # Log level for Loguru
    log_level: str = "info"

    # Max HTTPX concurrent requests for async calls to Blizzard (cache updates)
    max_concurrent_requests: int = 5

    ############
    # REDIS CONFIGURATION
    ############

    # Whether or not you want to use Redis as a cache system for the API. Mainly
    # used to avoid useless calls to Blizzard HTML pages (profiles can take from
    # 2 to 5 seconds to load...). Enabled by default.
    redis_caching_enabled: bool = True

    # Redis server host
    redis_host: str = "127.0.0.1"

    # Redis server port
    redis_port: int = 6379

    ############
    # CACHE CONFIGURATION
    ############

    # Whether or not you want to use the API Cache directly in the app (GET).
    # Disabled by default, because we are using the reverse proxy (nginx) to
    # request the API Cache first, before calling Fast API server.
    use_api_cache_in_app: bool = False

    # Prefix for keys in API Cache with entire payload (Redis).
    # Used by nginx as main API cache.
    api_cache_key_prefix: str = "api-cache"

    # Prefix for keys in Parser cache (Redis). Used by parser classes
    # in order to avoid parsing data which has already been parsed.
    parser_cache_key_prefix: str = "parser-cache"

    # Prefix for keys in Parser cache last update (Redis).
    # Used by the Parser Cache expiration system, to avoid keeping Parser
    # Cache data which is not used anymore indefinitely.
    parser_cache_last_update_key_prefix: str = "parser-cache-last-update"

    # When a cache value is about the expire (less than the configured value),
    # we will refresh it in the automatic cronjob "check_and_update_cache"
    # which is launched every minute. The value is specified in seconds.
    expired_cache_refresh_limit: int = 3600

    # Cache TTL for heroes list data (seconds)
    heroes_path_cache_timeout: int = 86400

    # Cache TTL for specific hero data (seconds)
    hero_path_cache_timeout: int = 86400

    # Cache TTL for Blizzard homepage data : gamemodes and roles (seconds)
    home_path_cache_timeout: int = 86400

    # Cache TTL for career pages data (seconds)
    career_path_cache_timeout: int = 7200

    # Cache TTL for search account data (seconds)
    search_account_path_cache_timeout: int = 3600

    # TTL for Parser Cache expiration system (seconds)
    # Used in order to make the Parser Cache expire if the player career data
    # hasn't been retrieved from an API call since a certain amount of time
    career_parser_cache_expiration_timeout: int = 604800

    # In order to fluidify the parser cache refresh, and to avoid having a lot
    # of refresh in the same time, we're using a random percentage spread value.
    # It must be a value included between 0 and 100. For example, with 3600 as
    # a timeout, and 25% of spreading, we have a spreading value of 900 = 25% * 3600.
    # The expiration value will be between 2700 (3600 - 900) and 4500 (3600 + 900).
    parser_cache_expiration_spreading_percentage: int = 25

    ############
    # NAMECARDS
    ############

    # Cache key for namecard cache in Redis.
    namecard_cache_key_prefix: str = "namecard-cache"

    # URI of the page where namecards are saved
    namecards_path: str = "/en-us/search/"

    # Cache TTL for namecards list
    namecards_timeout: int = 7200

    ############
    # BLIZZARD
    ############

    # Blizzard base url for Overwatch website
    blizzard_host: str = "https://overwatch.blizzard.com"

    # Blizzard home page with some details
    home_path: str = "/"

    # Route for Overwatch heroes pages
    heroes_path: str = "/heroes"

    # Route for players career pages
    career_path: str = "/career"

    # Route for searching Overwatch accounts by name
    search_account_path: str = "/search/account-by-name"

    ############
    # CRITICAL ERROR DISCORD WEBHOOK
    ############

    # Enable Discord Webhook for critical errors or not
    discord_webhook_enabled: bool = False

    # Discord Webhook URL
    discord_webhook_url: str = ""

    ############
    # LOCAL
    ############

    # Root path for test fixtures, used to update test data when Blizzard pages are updated
    # It should never be overriden in dotenv.
    test_fixtures_root_path: str = f"{Path.cwd()}/tests/fixtures"

    # Root path for Loguru access logs. It should never be overriden in dotenv.
    logs_root_path: str = f"{Path.cwd()}/logs"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
