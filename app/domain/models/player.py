"""Player domain model dataclasses."""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


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


@dataclass
class PlayerRequest:
    """Parameter object for a player data request.

    Pass a single ``PlayerRequest`` to ``PlayerService._execute_player_request``
    instead of passing each field as a separate keyword argument.
    """

    player_id: str
    cache_key: str
    data_factory: Callable[[str, dict], dict]
