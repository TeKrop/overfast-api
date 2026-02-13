"""Helper functions for monitoring and metrics

Provides utilities for normalizing endpoint paths to avoid high cardinality
in Prometheus metrics (replacing dynamic segments like player IDs with placeholders).
"""

import re
from urllib.parse import urlparse


def normalize_endpoint(path: str) -> str:
    """
    Normalize endpoint path by replacing dynamic segments with placeholders

    Replaces player IDs and hero keys with placeholders to avoid high cardinality
    in Prometheus labels. This allows metrics to be aggregated by endpoint pattern
    rather than by individual resource IDs.

    IMPORTANT: This logic is duplicated in build/nginx/prometheus_log.conf for Nginx.
    When modifying these patterns, update BOTH implementations.
    See app/monitoring/README.md for synchronization guidelines.

    Args:
        path: Raw request path (e.g., "/players/TeKrop-2217/summary")

    Returns:
        Normalized path (e.g., "/players/{player_id}/summary")

    Examples:
        >>> normalize_endpoint("/players/TeKrop-2217/summary")
        '/players/{player_id}/summary'
        >>> normalize_endpoint("/players/TeKrop-2217/stats/career")
        '/players/{player_id}/stats/career'
        >>> normalize_endpoint("/heroes/ana")
        '/heroes/{hero_key}'
        >>> normalize_endpoint("/heroes/stats")
        '/heroes/stats'
        >>> normalize_endpoint("/heroes")
        '/heroes'
    """
    # Normalize player paths: /players/<player_id>/... → /players/{player_id}/...
    # Player IDs match pattern: username-12345 or username#12345
    path = re.sub(
        r"^/players/[^/]+(/.*)?$",
        r"/players/{player_id}\1",
        path,
    )

    # Normalize hero paths: /heroes/<hero_key> → /heroes/{hero_key}
    # Match single segment after /heroes/ that is NOT "stats"
    # This preserves /heroes/stats while normalizing /heroes/ana
    if path.startswith("/heroes/") and path != "/heroes/stats":
        # Check if it's a single segment (hero key) or has more segments
        segments = path[len("/heroes/") :].split("/")
        if segments[0] and segments[0] != "stats":
            # Replace the hero key with placeholder
            path = "/heroes/{hero_key}" + (
                "/" + "/".join(segments[1:]) if len(segments) > 1 else ""
            )

    return path


def normalize_blizzard_url(url: str) -> str:
    """
    Normalize a Blizzard URL to a pattern for Prometheus labels.

    Extracts the path from a full Blizzard URL and replaces dynamic segments
    (player names, hero keys, search terms, locale) with placeholders.

    Args:
        url: Full Blizzard URL (e.g., "https://overwatch.blizzard.com/en-us/career/TeKrop-2217/")

    Returns:
        Normalized path pattern (e.g., "/career/{player_id}")

    Examples:
        >>> normalize_blizzard_url("https://overwatch.blizzard.com/en-us/career/TeKrop-2217/")
        '/career/{player_id}'
        >>> normalize_blizzard_url("https://overwatch.blizzard.com/en-us/heroes/ana/")
        '/heroes/{hero_key}'
        >>> normalize_blizzard_url("https://overwatch.blizzard.com/en-us/heroes/")
        '/heroes'
        >>> normalize_blizzard_url("https://overwatch.blizzard.com/en-us/search/account-by-name/TeKrop/")
        '/search/account-by-name/{search_name}'
        >>> normalize_blizzard_url("https://overwatch.blizzard.com/en-us/rates/data/")
        '/rates/data'
        >>> normalize_blizzard_url("https://overwatch.blizzard.com/en-us/")
        '/'
    """
    path = urlparse(url).path.rstrip("/")

    # Strip locale prefix (e.g., /en-us, /fr-fr, /ko-kr)
    path = re.sub(r"^/[a-z]{2}-[a-z]{2}", "", path)

    # Normalize career pages: /career/<player_id> → /career/{player_id}
    path = re.sub(r"^/career/[^/]+", "/career/{player_id}", path)

    # Normalize hero pages: /heroes/<hero_key> → /heroes/{hero_key}
    if re.match(r"^/heroes/[^/]+", path):
        path = "/heroes/{hero_key}"

    # Normalize search: /search/account-by-name/<name> → /search/account-by-name/{search_name}
    path = re.sub(
        r"^/search/account-by-name/[^/]+",
        "/search/account-by-name/{search_name}",
        path,
    )

    return path or "/"
