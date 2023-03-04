"""Project constants module"""
import tomllib
from pathlib import Path

with Path(f"{Path.cwd()}/pyproject.toml").open(mode="rb") as project_file:
    project_data = tomllib.load(project_file)

OVERFAST_API_VERSION = project_data["tool"]["poetry"]["version"]

OVERFAST_API_BASE_URL = "https://overfast-api.tekrop.fr"

############
# REDIS CONFIGURATION
############

# Whether or not you want to use Redis as a cache system for the API. Mainly used to avoid
# useless calls to Blizzard HTML pages (profiles can take from 2 to 5 seconds to load...)
# Enabled by default.
REDIS_CACHING_ENABLED = True

# Redis server host
REDIS_HOST = "redis"

# Redis server port
REDIS_PORT = 6379

############
# CACHE CONFIGURATION
############

# Max HTTPX concurrent requests for cache updates
MAX_CONCURRENT_REQUESTS = 5

# Whether or not you want to use the API Cache directly in the app (GET). Disabled by default,
# because we are using the reverse proxy (nginx) to request the API Cache first, before
# calling Fast API server.
USE_API_CACHE_IN_APP = False

# Prefix for keys in API Cache with entire payload (Redis). Used by nginx as main API cache.
API_CACHE_KEY_PREFIX = "api-cache"

# Prefix for keys in Parser cache (Redis). Used by parser in order to avoid parsing unchanged data.
PARSER_CACHE_KEY_PREFIX = "parser-cache"

# When a cache value is about the expire (less than the configured value), we will
# refresh it in the automatic cronjob "check_and_update_cache" (launched every minute)
EXPIRED_CACHE_REFRESH_LIMIT = 1800

# Once a day
HEROES_PATH_CACHE_TIMEOUT = 86400

# Once a day
HERO_PATH_CACHE_TIMEOUT = 86400

# Once a day
HOME_PATH_CACHE_TIMEOUT = 86400

# One hour
CAREER_PATH_CACHE_TIMEOUT = 3600

# One hour
SEARCH_ACCOUNT_PATH_CACHE_TIMEOUT = 3600

############
# BLIZZARD
############

# Blizzard base url for Overwatch website
BLIZZARD_HOST = "https://overwatch.blizzard.com"

# Blizzard home page with some details
HOME_PATH = "/"

# Route for Overwatch heroes pages
HEROES_PATH = "/heroes"

# Route for players career pages
CAREER_PATH = "/career"

# Route for searching Overwatch accounts by name
SEARCH_ACCOUNT_PATH = "/search/account-by-name"

############
# CRITICAL ERROR DISCORD WEBHOOK
############

# Enable Discord Webhook for critical errors or not
DISCORD_WEBHOOK_ENABLED = False

# Discord Webhook URL
DISCORD_WEBHOOK_URL = ""

############
# LOCAL
############

# Root path for test fixtures, used to update test data when Blizzard pages are updated
TEST_FIXTURES_ROOT_PATH = f"{Path.cwd()}/tests/fixtures"

# Root path for Loguru access logs
LOGS_ROOT_PATH = f"{Path.cwd()}/logs"

# Log level for Loguru
LOG_LEVEL = "info"
