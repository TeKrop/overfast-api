"""Set of pydantic models used for Players API routes"""
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    HttpUrl,
    StrictFloat,
    StrictInt,
    create_model,
)

from app.common.api_examples import (
    CareerStatsExample,
    HeroesComparisonsExample,
    PlayerCareerStatsExample,
    PlayerStatsSummaryExample,
)
from app.common.enums import (
    CareerStatCategory,
    CompetitiveDivision,
    HeroKey,
    PlayerPrivacy,
)
from app.common.helpers import get_hero_name, key_to_label


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
    avatar: HttpUrl | None = Field(
        None,
        description="URL of the player's avatar. Can be null if couldn't retrieve any",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/daeddd96e58a2150afa6ffc3c5503ae7f96afc2e22899210d444f45dee508c6c.png",
    )
    namecard: HttpUrl | None = Field(
        None,
        description="URL of the player's namecard (or banner) if any",
        example="https://d15f34w2p8l1cc.cloudfront.net/overwatch/55d8c21e9d8b14942c26c4028059b6cd3b4e2fea40a139821ecee73a0005126f.png",
    )
    title: str | None = Field(
        None, description="Title of the player if any", example="Bytefixer"
    )
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


class CareerStatsConfig:
    schema_extra = {"example": CareerStatsExample}


CareerStats = create_model(
    "CareerStats",
    all_heroes=(
        list[HeroCareerStats] | None,
        Field(
            None,
            description="Total of statistics for all heroes",
            alias="all-heroes",
            min_items=1,
        ),
    ),
    **{
        hero_key.name.lower(): (
            list[HeroCareerStats] | None,
            Field(
                None,
                description=f"Career statistics for {get_hero_name(hero_key)}",
                alias=hero_key.value,
                min_items=1,
            ),
        )
        for hero_key in HeroKey
    },
    __config__=CareerStatsConfig,
)


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


# Player stats summary
class TotalStatsSummary(BaseModel):
    eliminations: int = Field(..., description="Total number of eliminations", ge=0)
    assists: int = Field(..., description="Total number of assists", ge=0)
    deaths: int = Field(..., description="Total number of deaths", ge=0)
    damage: int = Field(..., description="Total damage done", ge=0)
    healing: int = Field(..., description="Total healing done", ge=0)


class AverageStatsSummary(BaseModel):
    eliminations: float = Field(
        ..., description="Average eliminations per 10 minutes", ge=0.0
    )
    assists: float = Field(..., description="Average assists per 10 minutes", ge=0.0)
    deaths: float = Field(..., description="Average deaths per 10 minutes", ge=0.0)
    damage: float = Field(..., description="Average damage done per 10 minutes", ge=0.0)
    healing: float = Field(
        ..., description="Average healing done per 10 minutes", ge=0.0
    )


class StatsSummary(BaseModel):
    games_played: int = Field(..., description="Number of games played", ge=0)
    games_won: int = Field(..., description="Number of games won", ge=0)
    games_lost: int = Field(..., description="Number of games lost", ge=0)
    time_played: int = Field(..., description="Time played (in seconds)", ge=0)
    winrate: float = Field(..., description="Winrate (in percent)", ge=0.0, le=100.0)
    kda: float = Field(..., description="Kill / Death / Assist ratio", ge=0.0)
    total: TotalStatsSummary = Field(
        ...,
        description=(
            "Total values for generic stats : eliminations, assists, "
            "deaths, damage, healing"
        ),
    )
    average: AverageStatsSummary = Field(
        ...,
        description=(
            "Average values per 10 minutes for generic stats : eliminations, "
            "assists, deaths, damage, healing"
        ),
    )


class PlayerRolesStats(BaseModel):
    tank: StatsSummary | None = Field(
        None,
        description=(
            "Stats summary of all tank heroes played by the player. "
            "Not defined if he never played this role."
        ),
    )
    damage: StatsSummary | None = Field(
        None,
        description=(
            "Stats summary of all damage heroes played by the player. "
            "Not defined if he never played this role."
        ),
    )
    support: StatsSummary | None = Field(
        None,
        description=(
            "Stats summary of all support heroes played by the player. "
            "Not defined if he never played this role."
        ),
    )


PlayerHeroesStats = create_model(
    "PlayerHeroesStats",
    **{
        hero_key.name.lower(): (
            StatsSummary | None,
            Field(
                None,
                description=(
                    f"Stats summary for {get_hero_name(hero_key)}. "
                    "Not defined if he never played the hero."
                ),
                alias=hero_key.value,
            ),
        )
        for hero_key in HeroKey
    },
)


class PlayerStatsSummary(BaseModel):
    general: StatsSummary | None = Field(
        None,
        description="Sum of the stats of all the heroes played by the player",
    )
    roles: PlayerRolesStats | None = Field(
        None,
        description=(
            "Sum of the stats of all the heroes played by the player, regrouped by roles"
        ),
    )
    heroes: PlayerHeroesStats | None = Field(
        None, description="Stats of all the heroes played by the player"
    )

    class Config:
        schema_extra = {"example": PlayerStatsSummaryExample}


class PlayerCareerStatsConfig:
    schema_extra = {"example": PlayerCareerStatsExample}


# Player career stats
HeroPlayerCareerStats = create_model(
    "HeroPlayerCareerStats",
    **{
        stat_category.name.lower(): (
            dict[str, StrictInt | StrictFloat] | None,
            Field(
                None,
                description=(
                    f'Statistics for "{key_to_label(stat_category.value)}" category'
                ),
                alias=stat_category.value,
            ),
        )
        for stat_category in CareerStatCategory
    },
)


PlayerCareerStats = create_model(
    "PlayerCareerStats",
    all_heroes=(
        HeroPlayerCareerStats | None,
        Field(
            None,
            description="Total of statistics for all heroes",
            alias="all-heroes",
        ),
    ),
    **{
        hero_key.name.lower(): (
            HeroPlayerCareerStats | None,
            Field(
                None,
                description=f"Career statistics for {get_hero_name(hero_key)}",
                alias=hero_key.value,
            ),
        )
        for hero_key in HeroKey
    },
    __config__=PlayerCareerStatsConfig,
)
