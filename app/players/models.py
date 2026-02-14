"""Set of pydantic models used for Players API routes"""

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictFloat,
    StrictInt,
    create_model,
)

from .api_examples import (
    CareerStatsExample,
    HeroesComparisonsExample,
    PlayerCareerStatsExample,
    PlayerStatsSummaryExample,
)
from .enums import (
    CareerStatCategory,
    CompetitiveDivision,
    HeroKey,
)
from .helpers import get_hero_name, key_to_label


# Player search
class PlayerShort(BaseModel):
    player_id: str = Field(
        ...,
        title="Player unique identifier",
        description="Identifier of the player, BattleTag if found, else Blizzard hexadecimal ID",
        examples=[
            "TeKrop-2217",
            "e651af82ba3ccafcbfa120%7C41daffa5861594b6cd5a6c27dc961232",
        ],
    )
    name: str = Field(
        ...,
        description="Player nickname displayed in the game",
        examples=["TeKrop"],
    )
    avatar: HttpUrl | None = Field(
        None,
        description="URL of the player's avatar. Can be null if couldn't retrieve any",
        examples=[
            "https://d15f34w2p8l1cc.cloudfront.net/overwatch/daeddd96e58a2150afa6ffc3c5503ae7f96afc2e22899210d444f45dee508c6c.png",
        ],
    )
    namecard: HttpUrl | None = Field(
        None,
        description="URL of the player's namecard (or banner) if any",
        examples=[
            "https://d15f34w2p8l1cc.cloudfront.net/overwatch/55d8c21e9d8b14942c26c4028059b6cd3b4e2fea40a139821ecee73a0005126f.png",
        ],
    )
    title: str | None = Field(
        ...,
        description="Title of the player if any",
        examples=["Bytefixer"],
    )
    career_url: AnyHttpUrl = Field(
        ...,
        title="Career URL",
        description="Player's career OverFast API URL (Get player career data)",
        examples=[
            "https://overfast-api.tekrop.fr/players/TeKrop-2217",
            "https://overfast-api.tekrop.fr/players/e651af82ba3ccafcbfa120%7C41daffa5861594b6cd5a6c27dc961232",
        ],
    )
    blizzard_id: str = Field(
        ...,
        title="Blizzard ID",
        description="Blizzard unique identifier of the player (hexadecimal)",
        examples=["c65b8798bc61d6ffbba120%7Ccfe9dd77a4382165e2b920bdcc035949"],
    )
    last_updated_at: int | None = Field(
        None,
        title="Timestamp",
        description=(
            "Last time the player profile was updated on Blizzard (timestamp). "
            "Can be null if couldn't retrieve any"
        ),
        examples=[1704209332],
    )
    is_public: bool | None = Field(
        None,
        title="Is public",
        description="Whether or not the player profile is public",
        examples=[True],
    )


class PlayerSearchResult(BaseModel):
    total: int = Field(..., description="Total number of results", examples=[42], ge=0)
    results: list[PlayerShort] = Field(..., description="List of players found")


# Player career
class PlayerCompetitiveRank(BaseModel):
    division: CompetitiveDivision = Field(
        ...,
        description="Division of the rank",
        examples=["diamond"],
    )
    tier: int = Field(
        ...,
        description="Tier inside the division, lower is better",
        examples=[3],
        ge=1,
        le=5,
    )
    role_icon: HttpUrl = Field(
        ...,
        description="URL the role icon",
        examples=[
            "https://static.playoverwatch.com/img/pages/career/icons/role/tank-f64702b684.svg#icon",
        ],
    )
    rank_icon: HttpUrl = Field(
        ...,
        description="URL of the division icon associated with the player rank",
        examples=[
            "https://static.playoverwatch.com/img/pages/career/icons/rank/Rank_MasterTier-7d3b85ba0d.png",
        ],
    )
    tier_icon: HttpUrl = Field(
        ...,
        description="URL of the tier icon associated with the player rank",
        examples=[
            "https://static.playoverwatch.com/img/pages/career/icons/rank/TierDivision_3-1de89374e2.png",
        ],
    )


class PlatformCompetitiveRanksContainer(BaseModel):
    season: int | None = Field(
        ...,
        description=(
            "Last competitive season played by the player. Can be 0 on Blizzard "
            "data for some reason, but can't explain what it means."
        ),
        examples=[3],
        ge=0,
    )
    tank: PlayerCompetitiveRank | None = Field(..., description="Tank role details")
    damage: PlayerCompetitiveRank | None = Field(..., description="Damage role details")
    support: PlayerCompetitiveRank | None = Field(
        ..., description="Support role details"
    )
    open: PlayerCompetitiveRank | None = Field(
        ..., description="Open Queue role details"
    )


class PlayerCompetitiveRanksContainer(BaseModel):
    pc: PlatformCompetitiveRanksContainer | None = Field(
        ...,
        description=(
            "Competitive ranks for PC and last season played on it. "
            "If the player doesn't play on this platform, it's null."
        ),
    )
    console: PlatformCompetitiveRanksContainer | None = Field(
        ...,
        description=(
            "Competitive ranks for console and last season played on it. "
            "If the player doesn't play on this platform, it's null."
        ),
    )


class PlayerEndorsement(BaseModel):
    level: int = Field(
        ...,
        description="Player Endorsement level. 0 if no information found.",
        examples=[3],
        ge=0,
        le=5,
    )
    frame: HttpUrl = Field(
        ...,
        description="URL of the endorsement frame corresponding to the level",
        examples=[
            "https://static.playoverwatch.com/img/pages/career/icons/endorsement/3-8ccb5f0aef.svg#icon",
        ],
    )


class HeroStat(BaseModel):
    hero: HeroKey = Field(...)  # ty: ignore[invalid-type-form]
    value: StrictInt | StrictFloat = Field(
        ...,
        description=(
            "Value of the statistic for the given hero. Duration values are in seconds."
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
        min_length=1,
    )


class PlayerSummary(BaseModel):
    username: str = Field(
        ...,
        description="Username of the player",
        examples=["TeKrop"],
    )
    avatar: HttpUrl | None = Field(
        None,
        description="URL of the player's avatar. Can be null if couldn't retrieve any",
        examples=[
            "https://d15f34w2p8l1cc.cloudfront.net/overwatch/daeddd96e58a2150afa6ffc3c5503ae7f96afc2e22899210d444f45dee508c6c.png",
        ],
    )
    namecard: HttpUrl | None = Field(
        None,
        description="URL of the player's namecard (or banner) if any",
        examples=[
            "https://d15f34w2p8l1cc.cloudfront.net/overwatch/55d8c21e9d8b14942c26c4028059b6cd3b4e2fea40a139821ecee73a0005126f.png",
        ],
    )
    title: str | None = Field(
        ...,
        description="Title of the player if any",
        examples=["Bytefixer"],
    )
    endorsement: PlayerEndorsement | None = Field(
        ...,
        description="Player endorsement details",
    )
    competitive: PlayerCompetitiveRanksContainer | None = Field(
        ...,
        description=(
            "Competitive ranking in the last season played by the player "
            "in different roles depending on the platform. If the career is private "
            "or if the player doesn't play competitive at all, it's null."
        ),
    )
    last_updated_at: int | None = Field(
        None,
        title="Timestamp",
        description=(
            "Last time the player profile was updated on Blizzard (timestamp). "
            "Can be null if couldn't retrieve any"
        ),
        examples=[1704209332],
    )


class HeroesComparisons(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": HeroesComparisonsExample})

    time_played: HeroesStats | None = Field(
        ...,
        description="Total time played for each hero (integer in seconds)",
    )
    games_won: HeroesStats | None = Field(
        ...,
        description="Number of games won for each hero (integer)",
    )
    win_percentage: HeroesStats | None = Field(
        ...,
        description="Winrate percentage for each hero (integer between 0 and 100)",
    )
    weapon_accuracy_best_in_game: HeroesStats | None = Field(
        ...,
        description="Best weapon accuracy in game for each hero (integer percent between 0 and 100)",
    )
    eliminations_per_life: HeroesStats | None = Field(
        ...,
        description="Eliminations per life for each hero (float)",
    )
    kill_streak_best: HeroesStats | None = Field(
        ...,
        description="Best kill streak in game for each hero (integer)",
    )
    multikill_best: HeroesStats | None = Field(
        ...,
        description="Best multikills statistic for each hero (integer)",
    )
    eliminations_avg_per_10_min: HeroesStats | None = Field(
        ...,
        description="Average eliminations per 10 minutes for each hero (float)",
    )
    deaths_avg_per_10_min: HeroesStats | None = Field(
        ...,
        description="Average deaths per 10 minutes for each hero (float)",
    )
    final_blows_avg_per_10_min: HeroesStats | None = Field(
        ...,
        description="Average final blows per 10 minutes for each hero (float)",
    )
    solo_kills_avg_per_10_min: HeroesStats | None = Field(
        ...,
        description="Average solo kills per 10 minutes for each hero (float)",
    )
    objective_kills_avg_per_10_min: HeroesStats | None = Field(
        ...,
        description="Average objective kills per 10 minutes for each hero (float)",
    )
    objective_time_avg_per_10_min: HeroesStats | None = Field(
        ...,
        description="Average objective time per 10 minutes for each hero in seconds (integer)",
    )
    hero_damage_done_avg_per_10_min: HeroesStats | None = Field(
        ...,
        description="Average damage done per 10 minutes for each hero (integer)",
    )
    healing_done_avg_per_10_min: HeroesStats | None = Field(
        ...,
        description="Average healing done per 10 minutes for each hero (integer)",
    )


class SingleCareerStat(BaseModel):
    key: str = Field(..., description="Statistic key")
    label: str = Field(..., description="Statistic label")
    value: StrictInt | StrictFloat = Field(..., description="Statistic value")


class HeroCareerStats(BaseModel):
    category: CareerStatCategory = Field(..., description="Stat category key")
    label: str = Field(..., description="Label of the stat category")
    stats: list[SingleCareerStat] = Field(
        ...,
        description="List of statistics associated with the category",
        min_length=1,
    )


CareerStats = create_model(  # ty: ignore[no-matching-overload]
    "CareerStats",
    __config__=ConfigDict(json_schema_extra={"example": CareerStatsExample}),
    all_heroes=(
        list[HeroCareerStats] | None,
        Field(
            None,
            description="Total of statistics for all heroes",
            alias="all-heroes",
            min_length=1,
        ),
    ),
    **{
        hero_key.name.lower(): (  # ty: ignore[unresolved-attribute]
            list[HeroCareerStats] | None,
            Field(
                None,
                description=f"Career statistics for {get_hero_name(hero_key)}",
                alias=hero_key.value,  # ty: ignore[unresolved-attribute]
                min_length=1,
            ),
        )
        for hero_key in HeroKey
    },
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
        ...,
        description=(
            "Quickplay statistics about heroes. "
            "If the player doesn't have stats for this gamemode, it's null."
        ),
    )
    competitive: PlayerGamemodeStats | None = Field(
        ...,
        description=(
            "Competitive statistics about heroes in the last season played by the player. "
            "If the player doesn't have stats for this gamemode, it's null."
        ),
    )


class PlayerStats(BaseModel):
    pc: PlayerPlatformStats | None = Field(
        ...,
        description=(
            "Player statistics on PC. "
            "If the player doesn't play on this platform, it's null."
        ),
    )
    console: PlayerPlatformStats | None = Field(
        ...,
        description=(
            "Player statistics on console. "
            "If the player doesn't play on this platform, it's null."
        ),
    )


class Player(BaseModel):
    summary: PlayerSummary = Field(
        ...,
        description="Player summary (avatar, endorsement, competitive ranks, etc.)",
    )
    stats: PlayerStats | None = Field(
        ...,
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
        ...,
        description="Average eliminations per 10 minutes",
        ge=0.0,
    )
    assists: float = Field(..., description="Average assists per 10 minutes", ge=0.0)
    deaths: float = Field(..., description="Average deaths per 10 minutes", ge=0.0)
    damage: float = Field(..., description="Average damage done per 10 minutes", ge=0.0)
    healing: float = Field(
        ...,
        description="Average healing done per 10 minutes",
        ge=0.0,
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


PlayerHeroesStats = create_model(  # ty: ignore[no-matching-overload]
    "PlayerHeroesStats",
    **{
        hero_key.name.lower(): (  # ty: ignore[unresolved-attribute]
            StatsSummary | None,
            Field(
                None,
                description=(
                    f"Stats summary for {get_hero_name(hero_key)}. "
                    "Not defined if he never played the hero."
                ),
                alias=hero_key.value,  # ty: ignore[unresolved-attribute]
            ),
        )
        for hero_key in HeroKey
    },
)


class PlayerStatsSummary(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": PlayerStatsSummaryExample})

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
        None,
        description="Stats of all the heroes played by the player",
    )


# Player career stats
HeroPlayerCareerStats = create_model(  # ty: ignore[no-matching-overload]
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


PlayerCareerStats = create_model(  # ty: ignore[no-matching-overload]
    "PlayerCareerStats",
    __config__=ConfigDict(json_schema_extra={"example": PlayerCareerStatsExample}),
    all_heroes=(
        HeroPlayerCareerStats | None,
        Field(
            None,
            description="Total of statistics for all heroes",
            alias="all-heroes",
        ),
    ),
    **{
        hero_key.name.lower(): (  # ty: ignore[unresolved-attribute]
            HeroPlayerCareerStats | None,
            Field(
                None,
                description=f"Career statistics for {get_hero_name(hero_key)}",
                alias=hero_key.value,  # ty: ignore[unresolved-attribute]
            ),
        )
        for hero_key in HeroKey
    },
)


class PlayerParserErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the player parser error",
        examples=["Player not found"],
    )


class PlayerNotFoundError(BaseModel):
    """
    Enhanced 404 error response for unknown players with retry information.

    When a player is not found, the API implements exponential backoff to avoid
    repeatedly checking Blizzard for non-existent players. This response includes
    timing information to help clients implement intelligent retry logic.
    """

    error: str = Field(
        ...,
        description="Error message",
        examples=["Player not found"],
    )
    retry_after: int = Field(
        ...,
        description=(
            "Seconds to wait before retrying this request. "
            "Follows exponential backoff with settings: "
            "base=600s (10min), multiplier=3, max=21600s (6h). "
            "Progression: 600s → 1800s → 5400s → 21600s (capped)"
        ),
        examples=[600, 1800, 5400, 21600],
        gt=0,
    )
    next_check_at: int = Field(
        ...,
        description=(
            "Unix timestamp indicating when retries will be accepted. "
            "The API does NOT automatically check the player after this time. "
            "Instead, when a user retries after this timestamp, the API will "
            "attempt to fetch fresh data from Blizzard."
        ),
        examples=[1708098000],
        gt=0,
    )
    check_count: int = Field(
        ...,
        description=(
            "Number of times the API has attempted to fetch this player from Blizzard. "
            "Used to calculate exponential backoff delay."
        ),
        examples=[1, 2, 3, 4],
        ge=1,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Player not found",
                "retry_after": 1800,
                "next_check_at": 1739634000,
                "check_count": 2,
            }
        }
    )
