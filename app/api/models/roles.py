from pydantic import BaseModel, Field, HttpUrl

from app.domain.enums import Role


class RoleDetail(BaseModel):
    key: Role = Field(..., description="Key name of the role", examples=["damage"])
    name: str = Field(..., description="Name of the role", examples=["Damage"])
    icon: HttpUrl = Field(
        ...,
        description="Icon URL of the role",
        examples=[
            "https://blz-contentstack-images.akamaized.net/v3/assets/blt9c12f249ac15c7ec/bltc1d840ba007f88a8/62ea89572fdd1011027e605d/Damage.svg",
        ],
    )
    description: str = Field(
        ...,
        description="Description of the role",
        examples=[
            "Damage heroes seek out, engage, and obliterate the enemy with wide-ranging tools, abilities, and play styles. Fearsome but fragile, these heroes require backup to survive.",
        ],
    )
