# pylint: disable=C0301

"""Project constants module"""
import os

OVERFAST_API_VERSION = "2.0.3"

OVERFAST_API_BASE_URL = "https://overfast-api.tekrop.fr"

############
# REDIS CONFIGURATION
############

# Whether or not you want to use Redis as a cache system for the API. Mainly used to avoid
# useless calls to Blizzard HTML pages (profiles can take from 2 to 5 seconds to load...)
# Enabled by default.
REDIS_CACHING_ENABLED = True

# Redis server host
REDIS_HOST = "127.0.0.1"

# Redis server port
REDIS_PORT = 6379

############
# CACHE CONFIGURATION
############

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
EXPIRED_CACHE_REFRESH_LIMIT = 300

# Once a day
HEROES_PATH_CACHE_TIMEOUT = 86400

# Once a day
HERO_PATH_CACHE_TIMEOUT = 86400

# Once a day
HOME_PATH_CACHE_TIMEOUT = 86400

############
# BLIZZARD
############

# Blizzard base url for Overwatch website
BLIZZARD_HOST = "https://overwatch.blizzard.com"

# Blizzard home page with some details
HOME_PATH = "/en-us"

# Route for Overwatch heroes pages
HEROES_PATH = "/en-us/heroes"

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
TEST_FIXTURES_ROOT_PATH = f"{os.getcwd()}/tests/fixtures"

# Root path for Loguru access logs
LOGS_ROOT_PATH = f"{os.getcwd()}/logs"
