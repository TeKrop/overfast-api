"""Set of pydantic models used for Heroes API routes"""
from pydantic import BaseModel, Field, HttpUrl

from app.common.enums import HeroKey, MediaType, Role


class HitPoints(BaseModel):
    health: int = Field(..., description="Health of the hero", ge=1, example=200)
    armor: int = Field(..., description="Armor of the hero", ge=0, example=0)
    shields: int = Field(..., description="Shields of the hero", ge=0, example=0)
    total: int = Field(..., description="Total HP of the hero", ge=1, example=200)


class AbilityVideo(BaseModel):
    thumbnail: HttpUrl = Field(
        ...,
        description="Thumbnail of the ability video",
        example="https://images.blz-contentstack.com/v3/assets/blt2477dcaf4ebd440c/blt08db01a1d84b0c3b/6333c97e3922a2677fc88c3c/CASSIDY_COMBAT_ROLL.jpg",
    )
    link: HttpUrl = Field(
        ...,
        description="Link to the ability video (webm version)",
        example="https://assets.blz-contentstack.com/v3/assets/blt2477dcaf4ebd440c/bltcff86b9875852be9/6333c9873917977bfd986103/OVERWATCH_WEBSITE_CHARACTER_CAPTURE_CassidyPeacekeeper_WEB_16x9_1920x1080p30_H264.webm",
    )


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
    video: AbilityVideo = Field(..., description="Video of the ability")


class Media(BaseModel):
    type: MediaType = Field(..., description="Type of the media", example="video")
    link: HttpUrl = Field(
        ...,
        description="Link to the media",
        example="https://youtu.be/PKYVvPNhRR0",
    )


class StoryChapter(BaseModel):
    title: str = Field(..., description="Title of the chapter", example="Blackwatch")
    content: str = Field(
        ...,
        description="Content of the chapter",
        example=(
            "Cassidy had already made a name for himself as a member of the "
            "notorious Deadlock Rebels Gang, when he and his associates were "
            "busted in an Overwatch sting operation. With his expert marksmanship "
            "and resourcefulness, he was given the choice between rotting in a "
            "maximum-security lockup and joining Blackwatch, Overwatch's covert "
            "ops division. He chose the latter. Although he was initially cynical, "
            "he came to believe that he could make amends for his past sins by "
            "righting the injustices of the world. Cassidy appreciated the "
            "flexibility afforded to the clandestine Blackwatch, unhindered by "
            "bureaucracy and red tape. But as Overwatch's influence waned, rogue "
            "elements within Blackwatch sought to bring down the organization and "
            "turn it to their own ends. After the destruction of Overwatch's Swiss "
            "HQ, Cassidy wanted no part of the infighting. He set off alone and "
            "went underground."
        ),
    )
    picture: HttpUrl = Field(
        ...,
        description="URL of the picture illustrating the chapter",
        example="https://images.blz-contentstack.com/v3/assets/blt2477dcaf4ebd440c/blt1683656b69bedff7/638808d0273de01068bb2806/cassidy-01.jpg",
    )


class Story(BaseModel):
    summary: str = Field(
        ...,
        description="Brief summary of the origin story of the hero",
        example=(
            "A founding member of the notorious Deadlock Gang, Cassidy was "
            "eventually coerced into joining Blackwatch, Overwatch's covert-ops "
            "division. He came to believe he could make amends for his past by "
            "righting the world's injustices. But when Overwatch fell, Cassidy "
            "went underground, resurfacing later as a gunslinger for hire, "
            "fighting only for causes he believes are just."
        ),
    )
    media: Media | None = Field(
        None,
        description="Media concerning the hero (YouTube video, pdf story, etc.)",
    )
    chapters: list[StoryChapter] = Field(
        ...,
        title="Chapters of the story",
        description="List of chapters concerning the story of the hero",
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
    portrait: HttpUrl | None = Field(
        None,
        description="Portrait picture URL of the hero",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/6cfb48b5597b657c2eafb1277dc5eef4a07eae90c265fcd37ed798189619f0a5.png",
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
    hitpoints: HitPoints | None = Field(None, description="Hitpoints of the hero")
    abilities: list[Ability] = Field(
        ..., description="List of hero abilities", min_items=1
    )
    story: Story = Field(..., description="Story of the hero")


class HeroShort(BaseModel):
    key: HeroKey = Field(
        ...,
        description="Key name of the hero",
        example="ana",
    )
    name: str = Field(..., description="Name of the hero", example="Ana")
    portrait: HttpUrl = Field(
        ...,
        description="Portrait picture URL of the hero",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/3429c394716364bbef802180e9763d04812757c205e1b4568bc321772096ed86.png",
    )
    role: Role = Field(
        ...,
        description="Role of the hero",
        example="support",
    )


class RoleDetail(BaseModel):
    key: Role = Field(..., description="Key name of the role", example="damage")
    name: str = Field(..., description="Name of the role", example="Damage")
    icon: HttpUrl = Field(
        ...,
        description="Icon URL of the role",
        example="https://blz-contentstack-images.akamaized.net/v3/assets/blt9c12f249ac15c7ec/bltc1d840ba007f88a8/62ea89572fdd1011027e605d/Damage.svg",
    )
    description: str = Field(
        ...,
        description="Description of the role",
        example="Damage heroes seek out, engage, and obliterate the enemy with wide-ranging tools, abilities, and play styles. Fearsome but fragile, these heroes require backup to survive.",
    )
