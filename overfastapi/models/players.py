# pylint: disable=C0301,C0115
"""Set of pydantic models used for Players API routes"""

from typing import Optional, Union

from pydantic import AnyHttpUrl, BaseModel, Field, HttpUrl, StrictFloat, StrictInt

from overfastapi.common.api_examples import (
    CareerStatsExample,
    HeroesComparisonsExample,
    PlayerAchievementsContainerExample,
)
from overfastapi.common.enums import (
    CareerStatCategory,
    HeroKey,
    PlayerPlatform,
    PlayerPrivacy,
)


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
    level: int = Field(
        ...,
        title="Level",
        description="Player level value on Overwatch",
        example=2415,
        gt=0,
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


class PlayerLevel(BaseModel):
    value: int = Field(..., description="Player Overwatch level", example=2415, ge=1)
    border: HttpUrl = Field(
        ...,
        description="URL of the border image of the player (without stars)",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/ac14208753baf77110880020450fa4aa0121df0c344c32a2d20f77c18ba75db5.png",
    )
    rank: Optional[HttpUrl] = Field(
        None,
        description="If any, URL of the border stars image of the player",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/8de2fe5d938256a5725abe4b3655ee5e9067b7a1f4d5ff637d974eb9c2e4a1ea.png",
    )


class PlayerCompetitiveRank(BaseModel):
    role_icon: HttpUrl = Field(
        ...,
        description="URL the role icon",
        example="https://static.playoverwatch.com/img/pages/career/icon-tank-8a52daaf01.png",
    )
    skill_rating: int = Field(
        ..., description="Skill rating score for the role", ge=1, le=5000, example=3872
    )
    tier_icon: HttpUrl = Field(
        ...,
        description="URL of the tier icon associated to the skill rating score",
        example="https://d1u1mce87gyfbn.cloudfront.net/game/rank-icons/rank-MasterTier.png",
    )


class PlayerCompetitiveRanksContainer(BaseModel):
    tank: Optional[PlayerCompetitiveRank] = Field(None, description="Tank role details")
    damage: Optional[PlayerCompetitiveRank] = Field(
        None, description="Damage role details"
    )
    support: Optional[PlayerCompetitiveRank] = Field(
        None, description="Support role details"
    )


class EndorsementDistribution(BaseModel):
    shotcaller: float = Field(
        ..., description="Shotcaller score", ge=0, le=1, example=0.35
    )
    teammate: float = Field(..., description="Teammate score", ge=0, le=1, example=0.26)
    sportsmanship: float = Field(
        ..., description="Sportsmanship score", ge=0, le=1, example=0.39
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
    distribution: EndorsementDistribution = Field(
        ...,
        description=(
            "Distribution of the endorsement scores (shotcaller, "
            "teammate, sportsmanship). Total score is 1."
        ),
    )


class PlayerSummary(BaseModel):
    username: str = Field(..., description="Username of the player", example="TeKrop")
    avatar: HttpUrl = Field(
        ...,
        description="URL of the player's avatar",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/daeddd96e58a2150afa6ffc3c5503ae7f96afc2e22899210d444f45dee508c6c.png",
    )
    level: PlayerLevel = Field(...)
    competitive: Optional[PlayerCompetitiveRanksContainer] = Field(
        None, description="Competitive ranking in different roles"
    )
    endorsement: PlayerEndorsement = Field(...)
    games_won: Optional[int] = Field(
        None, description="Number of games won by the player", example=7143
    )
    platforms: list[PlayerPlatform] = Field(
        ...,
        title="Platform",
        description="List of platforms the player is playing Overwatch on",
        min_items=1,
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


class HeroStat(BaseModel):
    hero: HeroKey = Field(...)
    value: Union[StrictInt, StrictFloat] = Field(
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

    class Config:  # pylint: disable=R0903
        schema_extra = {"example": HeroesComparisonsExample}


class SingleCareerStat(BaseModel):
    key: str = Field(..., description="Statistic key")
    label: str = Field(..., description="Statistic label")
    value: Union[StrictInt, StrictFloat] = Field(..., description="Statistic value")


class HeroCareerStats(BaseModel):
    category: CareerStatCategory = Field(..., description="Stat category key")
    label: str = Field(..., description="Label of the stat category")
    stats: list[SingleCareerStat] = Field(
        ..., description="List of statistics associated with the category", min_items=1
    )


class CareerStats(BaseModel):
    all_heroes: Optional[list[HeroCareerStats]] = Field(
        None,
        description="Total of statistics for all heroes",
        alias="all-heroes",
        min_items=1,
    )
    ana: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Ana", min_items=1
    )
    ashe: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Ashe", min_items=1
    )
    baptiste: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Baptiste", min_items=1
    )
    bastion: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Bastion", min_items=1
    )
    brigitte: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Brigitte", min_items=1
    )
    cassidy: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Cassidy", min_items=1
    )
    dva: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for D.Va", min_items=1
    )
    doomfist: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Doomfist", min_items=1
    )
    echo: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Echo", min_items=1
    )
    genji: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Genji", min_items=1
    )
    hanzo: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Hanzo", min_items=1
    )
    junkrat: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Junkrat", min_items=1
    )
    lucio: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for L??cio", min_items=1
    )
    mei: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Mei", min_items=1
    )
    mercy: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Mercy", min_items=1
    )
    moira: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Moira", min_items=1
    )
    orisa: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Orisa", min_items=1
    )
    pharah: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Pharah", min_items=1
    )
    reaper: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Reaper", min_items=1
    )
    reinhardt: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Reinhardt", min_items=1
    )
    roadhog: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Roadhog", min_items=1
    )
    sigma: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Sigma", min_items=1
    )
    soldier_76: Optional[list[HeroCareerStats]] = Field(
        None,
        description="Career statistics for Soldier: 76",
        alias="soldier-76",
        min_items=1,
    )
    sombra: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Sombra", min_items=1
    )
    symmetra: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Symmetra", min_items=1
    )
    torbjorn: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Torbj??rn", min_items=1
    )
    tracer: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Tracer", min_items=1
    )
    widowmaker: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Widowmaker", min_items=1
    )
    winston: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Winston", min_items=1
    )
    wrecking_ball: Optional[list[HeroCareerStats]] = Field(
        None,
        description="Career statistics for Wrecking Ball",
        alias="wrecking-ball",
        min_items=1,
    )
    zarya: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Zarya", min_items=1
    )
    zenyatta: Optional[list[HeroCareerStats]] = Field(
        None, description="Career statistics for Zenyatta", min_items=1
    )

    class Config:  # pylint: disable=R0903
        schema_extra = {"example": CareerStatsExample}


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
    general: Optional[list[PlayerAchievement]] = Field(
        None, description="General achievements (player level, generic skills, etc.)"
    )
    damage: Optional[list[PlayerAchievement]] = Field(
        None, description="Achievements concerning damage heroes"
    )
    tank: Optional[list[PlayerAchievement]] = Field(
        None, description="Achievements concerning tank heroes"
    )
    support: Optional[list[PlayerAchievement]] = Field(
        None, description="Achievements concerning support heroes"
    )
    maps: Optional[list[PlayerAchievement]] = Field(
        None, description="Achievements concerning Overwatch maps"
    )
    events: Optional[list[PlayerAchievement]] = Field(
        None, description="Achievements concerning Overwatch events"
    )

    class Config:  # pylint: disable=R0903
        schema_extra = {"example": PlayerAchievementsContainerExample}


class Player(BaseModel):
    summary: PlayerSummary = Field(
        ..., description="Player summary (level, avatar, etc.)"
    )
    quickplay: Optional[PlayerStats] = Field(
        None,
        description=(
            "Quickplay statistics about heroes. "
            "If the player career is private, it's null."
        ),
    )
    competitive: Optional[PlayerStats] = Field(
        None,
        description=(
            "Competitive statistics about heroes. "
            "If the player career is private, it's null."
        ),
    )
    achievements: Optional[PlayerAchievementsContainer] = Field(
        None,
        description=(
            "Achievements unlocked by the player. "
            "If the player career is private, it's null."
        ),
    )
