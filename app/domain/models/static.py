"""Typed shapes of the static-data lists (maps, gamemodes, roles, heroes)."""

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
