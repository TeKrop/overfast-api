"""Player domain model dataclasses."""

from dataclasses import dataclass, field


@dataclass
class PlayerIdentity:
    """Result of player identity resolution.

    Groups the four fields that travel together after resolving a
    BattleTag or Blizzard ID to a canonical identity.
    """

    blizzard_id: str | None = field(default=None)
    player_summary: dict = field(default_factory=dict)
    cached_html: str | None = field(default=None)
    battletag_input: str | None = field(default=None)
