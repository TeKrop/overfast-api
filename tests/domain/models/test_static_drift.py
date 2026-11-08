"""Static TypedDicts must expose the same fields as the API response models."""

from typing import TYPE_CHECKING

import pytest

from app.api.models.gamemodes import GamemodeDetails
from app.api.models.heroes import HeroShort
from app.api.models.maps import Map
from app.api.models.roles import RoleDetail
from app.domain.models.static import GamemodeEntry, HeroEntry, MapEntry, RoleEntry

if TYPE_CHECKING:
    from pydantic import BaseModel


@pytest.mark.parametrize(
    ("typed_dict", "model"),
    [
        (MapEntry, Map),
        (GamemodeEntry, GamemodeDetails),
        (RoleEntry, RoleDetail),
        (HeroEntry, HeroShort),
    ],
)
def test_typeddict_matches_pydantic_fields(
    typed_dict: type, model: type[BaseModel]
) -> None:
    assert set(typed_dict.__required_keys__) == set(model.model_fields)
