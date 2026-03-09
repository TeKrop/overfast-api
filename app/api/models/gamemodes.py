"""Set of pydantic models used for Gamemodes API routes"""

from pydantic import BaseModel, Field, HttpUrl

from app.domain.enums import MapGamemode


class GamemodeDetails(BaseModel):
    key: MapGamemode = Field(  # ty: ignore[invalid-type-form]
        ...,
        description=(
            "Key corresponding to the gamemode. Can be "
            "used as filter on the maps endpoint."
        ),
        examples=["push"],
    )
    name: str = Field(..., description="Name of the gamemode", examples=["Push"])
    icon: HttpUrl = Field(
        ...,
        description="Icon URL of the gamemode",
        examples=[
            "https://overfast-api.tekrop.fr/static/gamemodes/push-icon.svg",
        ],
    )
    description: str = Field(
        ...,
        description="Description of the gamemode",
        examples=[
            "Teams battle to take control of a robot and push it toward the enemy base.",
        ],
    )
    screenshot: HttpUrl = Field(
        ...,
        description="URL of an example screenshot of a map for the gamemode",
        examples=[
            "https://overfast-api.tekrop.fr/static/gamemodes/push.avif",
        ],
    )
