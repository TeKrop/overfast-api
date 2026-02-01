"""Set of pydantic models used for Maps API routes"""

from pydantic import BaseModel, Field, HttpUrl

from app.gamemodes.enums import MapGamemode

from .enums import MapKey


class Map(BaseModel):
    key: MapKey = Field(  # ty: ignore[invalid-type-form]
        ...,
        description="Key name of the map",
        examples=["aatlis"],
    )
    name: str = Field(..., description="Name of the map", examples=["Aatlis"])
    screenshot: HttpUrl = Field(
        ...,
        description="Screenshot of the map",
        examples=["https://overfast-api.tekrop.fr/static/maps/aatlis.jpg"],
    )
    gamemodes: list[MapGamemode] = Field(  # ty: ignore[invalid-type-form]
        ...,
        description="Main gamemodes on which the map is playable",
    )
    location: str = Field(
        ...,
        description="Location of the map",
        examples=["Morocco"],
    )
    country_code: str | None = Field(
        ...,
        min_length=2,
        max_length=2,
        description=(
            "Country Code of the location of the map. If not defined, it's null."
        ),
        examples=["MA"],
    )
