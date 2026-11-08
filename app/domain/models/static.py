"""Typed shapes of the static-data lists (maps, gamemodes, roles, heroes).

These mirror the Pydantic response models in ``app.api.models`` on purpose:
the domain layer cannot import from ``api`` (dependencies flow inward only),
so it needs its own typed shape. The API layer validates and serializes these
dicts into the Pydantic models at the router boundary.
``tests/domain/models/test_static_drift.py`` fails if the field names diverge.
"""

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from app.domain.enums import HeroGamemode


class MapEntry(TypedDict):
    key: str
    name: str
    screenshot: str
    gamemodes: list[str]
    uses: list[str]
    location: str
    country_code: str | None


class GamemodeEntry(TypedDict):
    key: str
    name: str
    icon: str
    description: str
    screenshot: str


class RoleEntry(TypedDict):
    key: str
    name: str
    icon: str | None
    description: str


class HeroEntry(TypedDict):
    key: str
    name: str
    portrait: str | None
    role: str | None
    subrole: str | None
    gamemodes: list[HeroGamemode]
