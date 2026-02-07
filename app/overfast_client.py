"""
OverFast HTTP client - DEPRECATED, moved to app/adapters/blizzard/client.py

This module is kept for backward compatibility during the migration to v4.
Import from app.adapters.blizzard instead.
"""

from app.adapters.blizzard import OverFastClient

__all__ = ["OverFastClient"]

