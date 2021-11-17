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


class WeaponAbility(BaseModel):
    name: str = Field(
        ..., description="Name of the weapon ability", example="Peacekeeper"
    )
    description: str = Field(
        ...,
        description="Description of the weapon ability",
        example="Accurate, powerful revolver.",
    )


class Weapon(BaseModel):
    icon: HttpUrl = Field(
        ...,
        description="Icon URL of the weapon",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/afb27d71eeb6f3635ac1ff236c7b3f9e3c6d017360ce022d5d384288ff95bce7.png",
    )
    primary_fire: WeaponAbility = Field(..., description="Primary fire ability")
    secondary_fire: Optional[WeaponAbility] = Field(
        None, description="Secondary fire ability"
    )


class Biography(BaseModel):
    real_name: str = Field(..., description="Real name of the hero", example="Cassidy")
    age: str = Field(
        ...,
        description="Age of the hero (string because some are not numbers)",
        example="37",
    )
    occupation: str = Field(
        ..., description="Occupation of the hero (job)", example="Bounty Hunter"
    )
    base_of_operations: str = Field(
        ...,
        description="Base of operations of the hero (location)",
        example="Santa Fe, New Mexico, USA",
    )
    affiliation: str = Field(
        ..., description="Affiliation of the hero", example="Overwatch (formerly)"
    )


class Story(BaseModel):
    biography: Biography = Field(...)
    catch_phrase: Optional[str] = Field(
        None,
        description="Catch phrase of the hero",
        example="Justice ain't gonna dispense itself.",
    )
    back_story: str = Field(
        ...,
        description="Long description of the story of the hero",
        example=(
            "Armed with his Peacekeeper revolver, the outlaw Cole Cassidy doles "
            "out justice on his own terms. On the run from the law as a young man, "
            "Cassidy became a founding member of the notorious Deadlock Gang, which "
            "trafficked in illicit weapons and military hardware throughout the "
            "American Southwest. Eventually, the gang’s luck ran out, and Overwatch "
            "busted Cassidy and several of his associates. With his expert marksmanship "
            "and resourcefulness, Cassidy was given the choice between rotting "
            "in a maximum-security lockup and joining Blackwatch, Overwatch's covert "
            "ops division. He chose the latter. Although initially cynical, Cassidy "
            "came to believe that he could make amends for his past by righting "
            "the injustices of the world. He appreciated the flexibility afforded "
            "to the clandestine Blackwatch, unhindered by bureaucracy and red tape. "
            "But as Overwatch's influence waned, rogue elements within Blackwatch "
            "sought to bring down the organization and turn it to their own ends. "
            "Wanting no part of the infighting, Cassidy set off alone. He resurfaced "
            "several years later as a gunslinger for hire. But while Cassidy's "
            "talents are sought after by parties great and small, he fights only "
            "for causes he believes are just."
        ),
    )


class Media(BaseModel):
    title: str = Field(
        ...,
        description="Title of the media (video title, picture description, story title, etc.)",
        example="Cassidy Gameplay Preview",
    )
    type: MediaType = Field(..., description="Type of the media", example="video")
    thumbnail: HttpUrl = Field(
        ...,
        description="Thumbnail picture of the media",
        example="https://images.blz-contentstack.com/v3/assets/blt2477dcaf4ebd440c/blt0432060c6878cdcd/5cef2102486d1c3d0af722f6/mccree-preview.jpg?auto=webp",
    )
    link: HttpUrl = Field(
        ...,
        description="Link to the media",
        example="https://www.youtube.com/watch?v=XkoRX2n9TSA",
    )


class Hero(BaseModel):
    name: str = Field(..., description="Name of the hero", example="Cassidy")
    role: Role = Field(
        ...,
        description="Role of the hero",
        example="damage",
    )
    difficulty: int = Field(
        ...,
        description="Difficulty of the hero (1 : easy, 3 : difficult)",
        example=2,
        ge=1,
        le=3,
    )
    description: str = Field(
        ...,
        description="Short description of the hero",
        example=(
            "Armed with his Peacekeeper revolver, Cassidy takes out targets with "
            "deadeye precision and dives out of danger with eagle-like speed."
        ),
    )
    weapons: list[Weapon] = Field(..., description="List of hero weapons", min_items=1)
    abilities: list[Ability] = Field(
        ..., description="List of hero abilities", min_items=1
    )
    story: Story = Field(...)
    medias: list[Media] = Field(
        ...,
        description="List of medias concerning the hero (videos, screenshots, pdf stories, etc.)",
        min_items=1,
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
