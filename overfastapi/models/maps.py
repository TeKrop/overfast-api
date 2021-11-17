# pylint: disable=C0301,C0115
"""Set of pydantic models used for Maps API routes"""
from pydantic import BaseModel, Field, HttpUrl

from overfastapi.common.enums import MapGamemode


class Map(BaseModel):
    name: str = Field(..., description="Name of the map", example="Hanamura")
    gamemodes: list[MapGamemode] = Field(
        ..., description="List of gamemodes on which the map can be played", min_items=1
    )
    thumbnail: HttpUrl = Field(
        ...,
        description="Thumbnail image representing the map",
        example="https://images.blz-contentstack.com/v3/assets/blt2477dcaf4ebd440c/bltea6af82310e86fd2/611ee47bc8163c2197c3c69c/hanamura.jpg?auto=webp",
    )
    flag: HttpUrl = Field(
        ...,
        description="Flag of the country where the map is located",
        example="https://images.blz-contentstack.com/v3/assets/blt2477dcaf4ebd440c/bltf133fe7583159e2d/611ee420d0cc27205271674f/Japan.png?auto=webp",
    )


class MapGamemodeDetails(BaseModel):
    key: MapGamemode = Field(
        ...,
        description="Key of the gamemode",
        example="escort",
    )
    name: str = Field(..., description="Full name of the gamemode", example="Escort")
    description: str = Field(
        ...,
        description="Description of the gamemode",
        example="Attackers escort a payload to a delivery point, while defenders strive to stop them.",
    )
