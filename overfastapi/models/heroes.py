# pylint: disable=C0301,C0115
"""Set of pydantic models used for Heroes API routes"""

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl

from overfastapi.common.enums import HeroKey, MediaType, Role


class Ability(BaseModel):
    name: str = Field(..., description="Name of the ability", example="Combat Roll")
    description: str = Field(
        ...,
        description="Description of the ability",
        example="Roll in the direction you're moving and reload.",
    )
    icon: HttpUrl = Field(
        ...,
        description="Icon URL of the ability",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/24a3f2f619859812bba6b6374513fa971b6b19ccb34950c02118b41cc4f93142.png",
    )


class Media(BaseModel):
    type: MediaType = Field(..., description="Type of the media", example="video")
    link: HttpUrl = Field(
        ...,
        description="Link to the media",
        example="https://youtu.be/PKYVvPNhRR0",
    )


class Hero(BaseModel):
    name: str = Field(..., description="Name of the hero", example="Cassidy")
    description: str = Field(
        ...,
        description="Short description of the hero",
        example=(
            "Armed with his Peacekeeper revolver, Cassidy takes out targets with "
            "deadeye precision and dives out of danger with eagle-like speed."
        ),
    )
    role: Role = Field(
        ...,
        description="Role of the hero",
        example="damage",
    )
    location: str = Field(
        ...,
        description="Location of the hero",
        example="Santa Fe, New Mexico, USA",
    )
    abilities: list[Ability] = Field(
        ..., description="List of hero abilities", min_items=1
    )
    story: str = Field(
        ...,
        description="Long description of the story of the hero",
        example=(
            "A founding member of the notorious Deadlock Gang, Cassidy was "
            "eventually coerced into joining Blackwatch, Overwatch’s covert-ops "
            "division. He came to believe he could make amends for his past by "
            "righting the world’s injustices. But when Overwatch fell, Cassidy "
            "went underground, resurfacing later as a gunslinger for hire, "
            "fighting only for causes he believes are just."
        ),
    )
    media: Optional[Media] = Field(
        None,
        description="Media concerning the hero (YouTube video, pdf story, etc.)",
    )


class HeroShort(BaseModel):
    key: HeroKey = Field(
        ...,
        description=("Key name of the hero"),
        example="ana",
    )
    name: str = Field(..., description="Name of the hero", example="Ana")
    portrait: HttpUrl = Field(
        ...,
        description="Portrait picture URL of the hero",
        example="https://d1u1mce87gyfbn.cloudfront.net/hero/ana/hero-select-portrait.png",
    )
    role: Role = Field(
        ...,
        description="Role of the hero",
        example="support",
    )
