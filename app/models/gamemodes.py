"""Set of pydantic models used for Gamemodes API routes"""

from pydantic import BaseModel, Field, HttpUrl

from app.common.enums import MapGamemode


class GamemodeDetails(BaseModel):
    key: MapGamemode = Field(
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
            "https://blz-contentstack-images.akamaized.net/v3/assets/blt9c12f249ac15c7ec/blt054b513cd6e95acf/62fd5b4a8972f93d1e325243/Push.svg",
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
            "https://blz-contentstack-images.akamaized.net/v3/assets/blt9c12f249ac15c7ec/blt93eefb6e91347639/62fc2d9eda42240856c1459c/Toronto_Push.jpg",
        ],
    )
