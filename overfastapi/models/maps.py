"""Set of pydantic models used for Maps API routes"""
from pydantic import BaseModel, Field, HttpUrl

from overfastapi.common.enums import MapGamemode


class Map(BaseModel):
    name: str = Field(..., description="Name of the map", example="Hanamura")
    screenshot: HttpUrl = Field(
        ...,
        description="Screenshot of the map",
        example="https://overfast-api.tekrop.fr/static/maps/hanamura.jpg",
    )
    gamemodes: list[MapGamemode] = Field(
        ..., description="Main gamemodes on which the map is playable"
    )
    location: str = Field(
        ..., description="Location of the map", example="Tokyo, Japan"
    )
    country_code: str | None = Field(
        None,
        min_length=2,
        max_length=2,
        description=(
            "Country Code of the location of the map. If not defined, it's null."
        ),
        example="JP",
    )
