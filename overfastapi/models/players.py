"""Set of pydantic models used for Players API routes"""
from pydantic import AnyHttpUrl, BaseModel, Field, HttpUrl, StrictFloat, StrictInt

from overfastapi.common.api_examples import CareerStatsExample, HeroesComparisonsExample
from overfastapi.common.enums import (
    CareerStatCategory,
    CompetitiveDivision,
    HeroKey,
    PlayerPrivacy,
)


# Player search
class PlayerShort(BaseModel):
    player_id: str = Field(
        ...,
        title="Player unique name",
        description='Identifier of the player : BattleTag (with "#" replaced by "-")',
        example="TeKrop-2217",
    )
    name: str = Field(
        ..., description="Player nickname displayed in the game", example="TeKrop#2217"
    )
    privacy: PlayerPrivacy = Field(
        ...,
        title="Privacy",
        description=(
            "Privacy of the player career. If private, only some basic informations "
            "are available on player details endpoint (avatar, endorsement)"
        ),
        example="public",
    )
    career_url: AnyHttpUrl = Field(
        ...,
        title="Career URL",
        description="Player's career OverFast API URL (Get player career data)",
        example="https://overfast-api.tekrop.fr/players/TeKrop-2217",
    )


class PlayerSearchResult(BaseModel):
    total: int = Field(..., description="Total number of results", example=42, ge=0)
    results: list[PlayerShort] = Field(..., description="List of players found")


# Player career
class PlayerCompetitiveRank(BaseModel):
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
        example="https://static.playoverwatch.com/img/pages/career/icons/role/tank-f64702b684.svg#icon",
    )
    rank_icon: HttpUrl = Field(
        ...,
        description="URL of the rank icon associated with the player rank (division + tier)",
        example="https://static.playoverwatch.com/img/pages/career/icons/rank/GrandmasterTier-3-e55e61f68f.png",
    )


class PlatformCompetitiveRanksContainer(BaseModel):
    tank: PlayerCompetitiveRank | None = Field(None, description="Tank role details")
    damage: PlayerCompetitiveRank | None = Field(
        None, description="Damage role details"
    )
    support: PlayerCompetitiveRank | None = Field(
        None, description="Support role details"
    )


class PlayerCompetitiveRanksContainer(BaseModel):
    pc: PlatformCompetitiveRanksContainer | None = Field(
        None,
        description=(
            "Competitive ranks for PC. "
            "If the player doesn't play on this platform, it's null."
        ),
    )
    console: PlatformCompetitiveRanksContainer | None = Field(
        None,
        description=(
            "Competitive ranks for console. "
            "If the player doesn't play on this platform, it's null."
        ),
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
        example="https://static.playoverwatch.com/img/pages/career/icons/endorsement/3-8ccb5f0aef.svg#icon",
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


class PlayerSummary(BaseModel):
    username: str = Field(..., description="Username of the player", example="TeKrop")
    avatar: HttpUrl = Field(
        ...,
        description="URL of the player's avatar",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/daeddd96e58a2150afa6ffc3c5503ae7f96afc2e22899210d444f45dee508c6c.png",
    )
    title: str = Field(None, description="Title of the player if any")
    endorsement: PlayerEndorsement = Field(...)
    competitive: PlayerCompetitiveRanksContainer | None = Field(
        None,
        description=(
            "Competitive ranking in different roles depending on the platform. "
            "If the career is private or if the player doesn't play competitive "
            "at all, it's null."
        ),
    )
    privacy: PlayerPrivacy = Field(
        ...,
        title="Privacy",
        description=(
            "Privacy of the player career. If private, only some basic informations "
            "are available (avatar, endorsement)"
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

    class Config:
        schema_extra = {"example": HeroesComparisonsExample}


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
    ramattra: list[HeroCareerStats] | None = Field(
        None, description="Career statistics for Ramattra", min_items=1
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

    class Config:
        schema_extra = {"example": CareerStatsExample}


class PlayerGamemodeStats(BaseModel):
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
            "(per 10 minutes), match awards (cards), hero specific, etc.)"
        ),
    )


class PlayerPlatformStats(BaseModel):
    quickplay: PlayerGamemodeStats | None = Field(
        None,
        description=(
            "Quickplay statistics about heroes. "
            "If the player doesn't have stats for this gamemode, it's null."
        ),
    )
    competitive: PlayerGamemodeStats | None = Field(
        None,
        description=(
            "Competitive statistics about heroes. "
            "If the player doesn't have stats for this gamemode, it's null."
        ),
    )


class PlayerStats(BaseModel):
    pc: PlayerPlatformStats | None = Field(
        None,
        description=(
            "Player statistics on PC. "
            "If the player doesn't play on this platform, it's null."
        ),
    )
    console: PlayerPlatformStats | None = Field(
        None,
        description=(
            "Player statistics on console. "
            "If the player doesn't play on this platform, it's null."
        ),
    )


class Player(BaseModel):
    summary: PlayerSummary = Field(
        ..., description="Player summary (avatar, endorsement, competitive ranks, etc.)"
    )
    stats: PlayerStats | None = Field(
        None,
        description=(
            "Player statistics (heroes comparisons, career stats, etc.). "
            "If the player career is private or has no stat at all, it's null."
        ),
    )
