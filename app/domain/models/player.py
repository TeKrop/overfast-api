"""Player domain model dataclasses."""

from dataclasses import dataclass, field
from typing import Any, TypedDict


@dataclass
class PlayerIdentity:
    """Result of player identity resolution.

    Groups the four fields that travel together after resolving a
    BattleTag or Blizzard ID to a canonical identity.
    """

    blizzard_id: str | None = field(default=None)
    player_summary: dict[str, Any] = field(default_factory=dict)
    cached_html: str | None = field(default=None)
    battletag_input: str | None = field(default=None)


class PlayerProfileCache(TypedDict):
    """Stored player profile as returned by ``get_player_profile_cache``."""

    profile: str
    summary: dict[str, Any]
    battletag: str | None
    name: str | None
    updated_at: int
