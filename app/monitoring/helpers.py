"""Helper functions for monitoring and metrics

Provides utilities for normalizing endpoint paths to avoid high cardinality
in Prometheus metrics (replacing dynamic segments like player IDs with placeholders).
"""

import re


def normalize_endpoint(path: str) -> str:
    """
    Normalize endpoint path by replacing dynamic segments with placeholders

    Replaces player IDs and hero keys with placeholders to avoid high cardinality
    in Prometheus labels. This allows metrics to be aggregated by endpoint pattern
    rather than by individual resource IDs.

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
