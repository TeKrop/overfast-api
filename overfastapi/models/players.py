"""Set of pydantic models used for Players API routes"""
from pydantic import AnyHttpUrl, BaseModel, Field, HttpUrl, StrictFloat, StrictInt

from overfastapi.common.enums import (
    CareerStatCategory,
    CompetitiveDivision,
    HeroKey,
    PlayerPlatform,
    PlayerPrivacy,
    Role,
)


# Player search
class PlayerShort(BaseModel):
    player_id: str = Field(
        ...,
        title="Player unique name",
        description=(
            'Identifier of the player : BattleTag (with "#" replaced by "-") for '
            "PC players, nickname for PSN/XBL players, nickname followed by "
            "hexadecimal id for Nintendo Switch."
        ),
        example="TeKrop-2217",
    )
    name: str = Field(
        ..., description="Player nickname displayed in the game", example="TeKrop#2217"
    )
    platform: PlayerPlatform = Field(
        ...,
        title="Platform",
        description="Platform on which the player is playing Overwatch",
        example="pc",
    )
    privacy: PlayerPrivacy = Field(
        ...,
        title="Privacy",
        description=(
            "Privacy of the player career. If private, only some basic informations "
            "are available on player details endpoint (level, avatar, endorsement)"
        ),
        example="public",
    )
    career_url: AnyHttpUrl = Field(
        ...,
        title="Career URL",
        description="Player's career OverFast API URL (Get player career data)",
        example="https://overfast-api.tekrop.fr/players/pc/TeKrop-2217",
    )


class PlayerSearchResult(BaseModel):
    total: int = Field(..., description="Total number of results", example=42, ge=0)
    results: list[PlayerShort] = Field(..., description="List of players found")


# Player career
class PlayerCompetitiveRank(BaseModel):
    role: Role = Field(
        ...,
        description="Role concerned by the rank",
        example="damage",
    )
    division: CompetitiveDivision = Field(
        ..., description="Division of the rank", example="diamond"
    )
    tier: int = Field(
        ...,
        description="Tier inside the division, lower is better",
        example=3,
        ge=1,
        le=5,
    )
    role_icon: HttpUrl = Field(
        ...,
        description="URL the role icon",
        example="https://static.playoverwatch.com/img/pages/career/icon-tank-8a52daaf01.png",
    )
    division_icon: HttpUrl = Field(
        ...,
        description="URL of the division icon associated with the player rank",
        example="https://d1u1mce87gyfbn.cloudfront.net/game/rank-icons/rank-MasterTier.png",
    )


class PlayerCompetitiveRanksContainer(BaseModel):
    tank: PlayerCompetitiveRank | None = Field(None, description="Tank role details")
    damage: PlayerCompetitiveRank | None = Field(
        None, description="Damage role details"
    )
    support: PlayerCompetitiveRank | None = Field(
        None, description="Support role details"
    )
    open_queue: PlayerCompetitiveRank | None = Field(
        None, description="Open queue rank details"
    )


class PlayerEndorsement(BaseModel):
    level: int = Field(
        ...,
        description="Player Endorsement level. 0 if no information found.",
        example=3,
        ge=0,
        le=5,
    )
    frame: HttpUrl = Field(
        ...,
        description="URL of the endorsement frame corresponding to the level",
        example="https://static.playoverwatch.com/svg/icons/endorsement-frames-3c9292c49d.svg#_2",
    )


class HeroStat(BaseModel):
    hero: HeroKey = Field(...)
    value: StrictInt | StrictFloat = Field(
        ...,
        description=(
            "Value of the statistic for the given hero. "
            "Duration values are in seconds."
        ),
    )


class HeroesStats(BaseModel):
    label: str = Field(..., description="Label of the hero statistic")
    values: list[HeroStat] = Field(
        ...,
        description=(
            "List of values of this statistic for each heroes. "
            "All heroes may not be included in the list."
        ),
        min_items=1,
    )


class OverwatchOneLevel(BaseModel):
    value: int = Field(
        ...,
        title="Level",
        description="Player level value on Overwatch 1",
        example=2415,
        ge=1,
    )
    border: HttpUrl = Field(
        ...,
        description="URL of the border image of the player (without stars)",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/ac14208753baf77110880020450fa4aa0121df0c344c32a2d20f77c18ba75db5.png",
    )
    rank: HttpUrl | None = Field(
        None,
        description="If any, URL of the border stars image of the player",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/8de2fe5d938256a5725abe4b3655ee5e9067b7a1f4d5ff637d974eb9c2e4a1ea.png",
    )


class PlayerSummary(BaseModel):
    username: str = Field(..., description="Username of the player", example="TeKrop")
    avatar: HttpUrl = Field(
        ...,
        description="URL of the player's avatar",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/daeddd96e58a2150afa6ffc3c5503ae7f96afc2e22899210d444f45dee508c6c.png",
    )
    banner: HttpUrl = Field(
        ...,
        description="URL of the player's banner",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/daeddd96e58a2150afa6ffc3c5503ae7f96afc2e22899210d444f45dee508c6c.png",
    )
    title: str = Field(None, description="Title of the player if any")
    competitive: PlayerCompetitiveRanksContainer | None = Field(
        None, description="Competitive ranking in different roles"
    )
    endorsement: PlayerEndorsement = Field(...)
    games_won: int | None = Field(
        None,
        title="Games Won",
        description="Number of games won by the player",
        example=7143,
    )
    platforms: list[PlayerPlatform] = Field(
        ...,
        title="Platform",
        description="List of platforms the player is playing Overwatch on",
        min_items=1,
    )
    overwatch_one_level: OverwatchOneLevel = Field(
        None,
        title="Overwatch 1 Level",
        description="Overwatch 1 Level details if the player played it",
    )
    privacy: PlayerPrivacy = Field(
        ...,
        title="Privacy",
        description=(
            "Privacy of the player career. If private, only some basic informations "
            "are available (level, avatar, endorsement)"
        ),
        example="public",
    )


class HeroesComparisons(BaseModel):
    time_played: HeroesStats = Field(
        None, description="Total time played for each hero (integer in seconds)"
    )
    games_won: HeroesStats = Field(
        None, description="Number of games won for each hero (integer)"
    )
    weapon_accuracy: HeroesStats = Field(
        None,
        description="Percentage of weapon accuracy for each hero (integer between 0 and 100)",
    )
    win_percentage: HeroesStats = Field(
        None,
        description="Winrate percentage for each hero (integer between 0 and 100)",
    )
    eliminations_per_life: HeroesStats = Field(
        None, description="Eliminations per life for each hero (float)"
    )
    critical_hit_accuracy: HeroesStats = Field(
        None,
        description="Critical hit accuracy percentage for each hero (integer between 0 and 100)",
    )
    multikill_best: HeroesStats = Field(
        None, description="Best multikills statistic for each hero (integer)"
    )
    objective_kills: HeroesStats = Field(
        None, description="Total number of objective kills for each hero (integer)"
    )

    # class Config:
    #     schema_extra = {"example": HeroesComparisonsExample}


class SingleCareerStat(BaseModel):
    key: str = Field(..., description="Statistic key")
    label: str = Field(..., description="Statistic label")
    value: StrictInt | StrictFloat = Field(..., description="Statistic value")


class HeroCareerStats(BaseModel):
    category: CareerStatCategory = Field(..., description="Stat category key")
    label: str = Field(..., description="Label of the stat category")
    stats: list[SingleCareerStat] = Field(
        ..., description="List of statistics associated with the category", min_items=1
    )


class CareerStats(BaseModel):
    all_heroes: list[HeroCareerStats] | None = Field(
        None,
        description="Total of statistics for all heroes",
        alias="all-heroes",
        min_items=1,
    )
    ana: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Ana", min_items=1
    )
    ashe: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Ashe", min_items=1
    )
    baptiste: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Baptiste", min_items=1
    )
    bastion: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Bastion", min_items=1
    )
    brigitte: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Brigitte", min_items=1
    )
    cassidy: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Cassidy", min_items=1
    )
    dva: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for D.Va", min_items=1
    )
    doomfist: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Doomfist", min_items=1
    )
    echo: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Echo", min_items=1
    )
    genji: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Genji", min_items=1
    )
    hanzo: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Hanzo", min_items=1
    )
    junker_queen: list[HeroCareerStats] | None = Field(
        None,
        description="Career statistics for Junker Queen",
        alias="junker-queen",
        min_items=1,
    )
    junkrat: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Junkrat", min_items=1
    )
    kiriko: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Kiriko", min_items=1
    )
    lucio: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Lúcio", min_items=1
    )
    mei: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Mei", min_items=1
    )
    mercy: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Mercy", min_items=1
    )
    moira: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Moira", min_items=1
    )
    orisa: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Orisa", min_items=1
    )
    pharah: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Pharah", min_items=1
    )
    reaper: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Reaper", min_items=1
    )
    reinhardt: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Reinhardt", min_items=1
    )
    roadhog: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Roadhog", min_items=1
    )
    sigma: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Sigma", min_items=1
    )
    soldier_76: list[HeroCareerStats] | None = Field(
        None,
        description="Career statistics for Soldier: 76",
        alias="soldier-76",
        min_items=1,
    )
    sojourn: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Sojourn", min_items=1
    )
    sombra: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Sombra", min_items=1
    )
    symmetra: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Symmetra", min_items=1
    )
    torbjorn: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Torbjörn", min_items=1
    )
    tracer: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Tracer", min_items=1
    )
    widowmaker: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Widowmaker", min_items=1
    )
    winston: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Winston", min_items=1
    )
    wrecking_ball: list[HeroCareerStats] | None = Field(
        None,
        description="Career statistics for Wrecking Ball",
        alias="wrecking-ball",
        min_items=1,
    )
    zarya: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Zarya", min_items=1
    )
    zenyatta: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Zenyatta", min_items=1
    )

    # class Config:
    #     schema_extra = {"example": CareerStatsExample}


class PlayerStats(BaseModel):
    heroes_comparisons: HeroesComparisons = Field(
        ...,
        description=(
            "List of general statistics on which heroes are compared for the player : "
            "total time played, number of games won, weapon accuracy, number of "
            "eliminations per life, etc.). Note that all heroes may not be included "
            "in every statistic objects."
        ),
    )
    career_stats: CareerStats = Field(
        ...,
        description=(
            "List of career statistics for every hero the player played :"
            " best statistics (most in game), combat (damage, kills, etc.), average "
            "(per 10 minutes), match awards (cards and medals), hero specific, etc.)"
        ),
    )


class PlayerAchievement(BaseModel):
    title: str = Field(..., description="Title of the achievement", example="Centenary")
    description: str = Field(
        ...,
        description="Description of the achievement",
        example="Win 100 games in Quick or Competitive Play.",
    )
    image: HttpUrl = Field(
        ...,
        description="Picture URL of the achievement",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/f5e73717ac598860557894a25d764adc86be9e8a39e19cba6680845d30545e8b.png",
    )


class PlayerAchievementsContainer(BaseModel):
    general: list[PlayerAchievement] | None = Field(
        None, description="General achievements (player level, generic skills, etc.)"
    )
    damage: list[PlayerAchievement] | None = Field(
        None, description="Achievements concerning damage heroes"
    )
    tank: list[PlayerAchievement] | None = Field(
        None, description="Achievements concerning tank heroes"
    )
    support: list[PlayerAchievement] | None = Field(
        None, description="Achievements concerning support heroes"
    )
    maps: list[PlayerAchievement] | None = Field(
        None, description="Achievements concerning Overwatch maps"
    )
    events: list[PlayerAchievement] | None = Field(
        None, description="Achievements concerning Overwatch events"
    )

    # class Config:
    #     schema_extra = {"example": PlayerAchievementsContainerExample}


class Player(BaseModel):
    summary: PlayerSummary = Field(
        ..., description="Player summary (level, avatar, etc.)"
    )
    quickplay: PlayerStats | None = Field(
        None,
        description=(
            "Quickplay statistics about heroes. "
            "If the player career is private, it's null."
        ),
    )
    competitive: PlayerStats | None = Field(
        None,
        description=(
            "Competitive statistics about heroes. "
            "If the player career is private, it's null."
        ),
    )
    achievements: PlayerAchievementsContainer | None = Field(
        None,
        description=(
            "Achievements unlocked by the player. "
            "If the player career is private, it's null."
        ),
    )
