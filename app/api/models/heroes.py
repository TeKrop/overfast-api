"""Set of pydantic models used for Heroes API routes"""

from pydantic import BaseModel, Field, HttpUrl

from app.domain.enums import BackgroundImageSize, HeroGamemode, HeroKey, MediaType, Role


class HeroBackground(BaseModel):
    url: HttpUrl = Field(
        ...,
        description="URL of the background image",
        examples=[
            "https://blz-contentstack-images.akamaized.net/v3/assets/blt2477dcaf4ebd440c/blt242e79efb1e27251/631a8b791566e20e82f30288/1600_Cassidy.jpg",
        ],
    )
    sizes: list[BackgroundImageSize] = Field(
        ...,
        description="Responsive breakpoint sizes for which this image is used",
        examples=[["md", "lg"]],
    )


class HitPoints(BaseModel):
    health: int = Field(..., description="Health of the hero", ge=1, examples=[250])
    armor: int = Field(..., description="Armor of the hero", ge=0, examples=[0])
    shields: int = Field(..., description="Shields of the hero", ge=0, examples=[0])
    total: int = Field(..., description="Total HP of the hero", ge=1, examples=[250])


class AbilityVideoLink(BaseModel):
    mp4: HttpUrl = Field(
        ...,
        description="MP4 version",
        examples=[
            "https://assets.blz-contentstack.com/v3/assets/blt2477dcaf4ebd440c/blt71688da0f7834fed/6333c9882dc7636608cc7078/OVERWATCH_WEBSITE_CHARACTER_CAPTURE_CassidyPeacekeeper_WEB_16x9_1920x1080p30_H264.mp4",
        ],
    )
    webm: HttpUrl = Field(
        ...,
        description="WebM version",
        examples=[
            "https://assets.blz-contentstack.com/v3/assets/blt2477dcaf4ebd440c/bltcff86b9875852be9/6333c9873917977bfd986103/OVERWATCH_WEBSITE_CHARACTER_CAPTURE_CassidyPeacekeeper_WEB_16x9_1920x1080p30_H264.webm",
        ],
    )


class AbilityVideo(BaseModel):
    thumbnail: HttpUrl = Field(
        ...,
        description="Thumbnail of the ability video",
        examples=[
            "https://images.blz-contentstack.com/v3/assets/blt2477dcaf4ebd440c/blt08db01a1d84b0c3b/6333c97e3922a2677fc88c3c/CASSIDY_COMBAT_ROLL.jpg",
        ],
    )
    link: AbilityVideoLink = Field(..., description="Link to the ability video")


class Ability(BaseModel):
    name: str = Field(..., description="Name of the ability", examples=["Combat Roll"])
    description: str = Field(
        ...,
        description="Description of the ability",
        examples=["Roll in the direction you're moving and reload."],
    )
    icon: HttpUrl = Field(
        ...,
        description="Icon URL of the ability",
        examples=[
            "https://d15f34w2p8l1cc.cloudfront.net/overwatch/24a3f2f619859812bba6b6374513fa971b6b19ccb34950c02118b41cc4f93142.png",
        ],
    )
    video: AbilityVideo = Field(..., description="Video of the ability")


class Media(BaseModel):
    type: MediaType = Field(..., description="Type of the media", examples=["video"])
    link: HttpUrl = Field(
        ...,
        description="Link to the media",
        examples=["https://youtu.be/PKYVvPNhRR0"],
    )


class StadiumPower(BaseModel):
    name: str = Field(..., description="Name of the power", examples=["Quick Draw"])
    description: str = Field(
        ...,
        description="Description of the power",
        examples=[
            "After using Combat Roll, Peacekeeper's next primary fire can auto-aim within 15m while under cooldown."
        ],
    )
    icon: HttpUrl = Field(
        ...,
        description="Icon URL of the power",
        examples=[
            "https://d15f34w2p8l1cc.cloudfront.net/overwatch/4ccb06c8fa111bf0cbe6d0c7812917df89a44f949601e24844b1fae0c3b89d4e.png",
        ],
    )


class StoryChapter(BaseModel):
    title: str = Field(..., description="Title of the chapter", examples=["Blackwatch"])
    content: str = Field(
        ...,
        description="Content of the chapter",
        examples=[
            (
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
        ],
    )
    picture: HttpUrl = Field(
        ...,
        description="URL of the picture illustrating the chapter",
        examples=[
            "https://images.blz-contentstack.com/v3/assets/blt2477dcaf4ebd440c/blt1683656b69bedff7/638808d0273de01068bb2806/cassidy-01.jpg",
        ],
    )


class Story(BaseModel):
    summary: str = Field(
        ...,
        description="Brief summary of the origin story of the hero",
        examples=[
            (
                "A founding member of the notorious Deadlock Gang, Cassidy was "
                "eventually coerced into joining Blackwatch, Overwatch's covert-ops "
                "division. He came to believe he could make amends for his past by "
                "righting the world's injustices. But when Overwatch fell, Cassidy "
                "went underground, resurfacing later as a gunslinger for hire, "
                "fighting only for causes he believes are just."
            ),
        ],
    )
    media: Media | None = Field(
        ...,
        description="Media concerning the hero (YouTube video, pdf story, etc.)",
    )
    chapters: list[StoryChapter] = Field(
        ...,
        title="Chapters of the story",
        description="List of chapters concerning the story of the hero",
    )


class Hero(BaseModel):
    name: str = Field(..., description="Name of the hero", examples=["Cassidy"])
    description: str = Field(
        ...,
        description="Short description of the hero",
        examples=[
            (
                "Armed with his Peacekeeper revolver, Cassidy takes out targets with "
                "deadeye precision and dives out of danger with eagle-like speed."
            ),
        ],
    )
    portrait: HttpUrl | None = Field(
        None,
        description=(
            "Portrait picture URL of the hero. On a hero release, "
            "can be null for a few days."
        ),
        examples=[
            "https://d15f34w2p8l1cc.cloudfront.net/overwatch/6cfb48b5597b657c2eafb1277dc5eef4a07eae90c265fcd37ed798189619f0a5.png",
        ],
    )
    backgrounds: list[HeroBackground] = Field(
        ...,
        description="List of background images for the hero, one per responsive breakpoint group.",
        examples=[
            [
                {
                    "url": "https://blz-contentstack-images.akamaized.net/v3/assets/blt2477dcaf4ebd440c/bltadb0bb2e726bee08/631a8b79be2fcf0db5eea4c8/960_Cassidy.jpg",
                    "sizes": ["min", "xs", "sm"],
                },
                {
                    "url": "https://blz-contentstack-images.akamaized.net/v3/assets/blt2477dcaf4ebd440c/blt242e79efb1e27251/631a8b791566e20e82f30288/1600_Cassidy.jpg",
                    "sizes": ["md", "lg"],
                },
                {
                    "url": "https://blz-contentstack-images.akamaized.net/v3/assets/blt2477dcaf4ebd440c/blt4bb4c31f6849c25b/631a8b781613910e6926bfd4/2600_Cassidy.jpg",
                    "sizes": ["xl+"],
                },
            ],
        ],
    )
    role: Role = Field(
        ...,
        description="Role of the hero",
        examples=["damage"],
    )
    location: str = Field(
        ...,
        description="Location of the hero",
        examples=["Santa Fe, New Mexico, USA"],
    )
    age: int | None = Field(
        ...,
        description="Age of the hero. Can be null if unknown.",
        ge=1,
        examples=[39],
    )
    birthday: str | None = Field(
        ...,
        description="Birthday of the hero. Can be null if unknown.",
        examples=["31 Jul"],
    )
    hitpoints: HitPoints | None = Field(
        None,
        description=(
            "Hitpoints of the hero. Can be null if hero data isn't in the CSV."
        ),
    )
    abilities: list[Ability] = Field(
        ...,
        description="List of hero abilities",
        min_length=1,
    )
    stadium_powers: list[StadiumPower] | None = Field(
        None,
        description="List of Stadium powers. Can be null if hero isn't available on Stadium gamemode.",
        min_length=12,
        max_length=12,
    )
    story: Story = Field(..., description="Story of the hero")


class HeroShort(BaseModel):
    key: HeroKey = Field(  # ty: ignore[invalid-type-form]
        ...,
        description="Key name of the hero",
        examples=["ana"],
    )
    name: str = Field(..., description="Name of the hero", examples=["Ana"])
    portrait: HttpUrl = Field(
        ...,
        description="Portrait picture URL of the hero",
        examples=[
            "https://d15f34w2p8l1cc.cloudfront.net/overwatch/3429c394716364bbef802180e9763d04812757c205e1b4568bc321772096ed86.png",
        ],
    )
    role: Role = Field(
        ...,
        description="Role of the hero",
        examples=["support"],
    )
    gamemodes: list[HeroGamemode] = Field(
        ...,
        description="List of gamemodes in which the hero is available",
        min_length=1,
        examples=[["stadium"]],
    )


class HeroParserErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the hero parser error",
        examples=["Hero not found or not released yet"],
    )


class HeroStatsSummary(BaseModel):
    hero: HeroKey = Field(  # ty: ignore[invalid-type-form]
        ..., description="Hero key used to identify Overwatch heroes in general"
    )
    pickrate: float = Field(..., description="Pickrate (in percent)", ge=0.0, le=100.0)
    winrate: float = Field(..., description="Winrate (in percent)", ge=0.0, le=100.0)


class BadRequestErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the error",
        examples=[
            "Selected map 'hanaoka' is not compatible with 'competitive' gamemode."
        ],
    )
