"""Set of pydantic models used for Maps API routes"""
from pydantic import BaseModel, Field, HttpUrl

from app.common.enums import MapGamemode


class Map(BaseModel):
    name: str = Field(..., description="Name of the map", examples=["Hanamura"])
    screenshot: HttpUrl = Field(
        ...,
        description="Screenshot of the map",
        examples=["https://overfast-api.tekrop.fr/static/maps/hanamura.jpg"],
    )
    gamemodes: list[MapGamemode] = Field(
        ...,
        description="Main gamemodes on which the map is playable",
    )
    location: str = Field(
        ...,
        description="Location of the map",
        examples=["Tokyo, Japan"],
    )
    country_code: str | None = Field(
        ...,
        min_length=2,
        max_length=2,
        description=(
            "Country Code of the location of the map. If not defined, it's null."
        ),
        examples=["JP"],
    )
