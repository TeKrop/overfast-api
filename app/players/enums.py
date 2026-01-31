from enum import StrEnum

from app.heroes.enums import HeroKey
from app.roles.enums import Role


class CareerStatCategory(StrEnum):
    """Categories of general statistics displayed in the players API"""

    ASSISTS = "assists"
    AVERAGE = "average"
    BEST = "best"
    COMBAT = "combat"
    GAME = "game"
    HERO_SPECIFIC = "hero_specific"
    MATCH_AWARDS = "match_awards"
    MISCELLANEOUS = "miscellaneous"


class CareerHeroesComparisonsCategory(StrEnum):
    """Categories of heroes stats in player comparisons"""

    TIME_PLAYED = "time_played"
    GAMES_WON = "games_won"
    WIN_PERCENTAGE = "win_percentage"
    WEAPON_ACCURACY_BEST_IN_GAME = "weapon_accuracy_best_in_game"
    ELIMINATIONS_PER_LIFE = "eliminations_per_life"
    KILL_STREAK_BEST = "kill_streak_best"
    MULTIKILL_BEST = "multikill_best"
    ELIMINATIONS_AVG_PER_10_MIN = "eliminations_avg_per_10_min"
    DEATHS_AVG_PER_10_MIN = "deaths_avg_per_10_min"
    FINAL_BLOWS_AVG_PER_10_MIN = "final_blows_avg_per_10_min"
    SOLO_KILLS_AVG_PER_10_MIN = "solo_kills_avg_per_10_min"
    OBJECTIVE_KILLS_AVG_PER_10_MIN = "objective_kills_avg_per_10_min"
    OBJECTIVE_TIME_AVG_PER_10_MIN = "objective_time_avg_per_10_min"
    HERO_DAMAGE_DONE_AVG_PER_10_MIN = "hero_damage_done_avg_per_10_min"
    HEALING_DONE_AVG_PER_10_MIN = "healing_done_avg_per_10_min"


# Dynamically create the HeroKeyCareerFilter by using the existing
# HeroKey enum and just adding the "all-heroes" option
HeroKeyCareerFilter = StrEnum(
    "HeroKeyCareerFilter",
    {
        "ALL_HEROES": "all-heroes",
        **{hero_key.name: hero_key.value for hero_key in HeroKey},  # ty: ignore[unresolved-attribute]
    },
)
HeroKeyCareerFilter.__doc__ = "Hero keys filter for career statistics endpoint"


# Dynamically create the CompetitiveRole enum by using the existing
# Role enum and just adding the "open" option for Open Queue
CompetitiveRole = StrEnum(
    "CompetitiveRole",
    {
        **{role.name: role.value for role in Role},
        "OPEN": "open",
    },
)
CompetitiveRole.__doc__ = "Competitive roles for ranks in stats summary"


class PlayerGamemode(StrEnum):
    """Gamemodes associated with players statistics"""

    QUICKPLAY = "quickplay"
    COMPETITIVE = "competitive"


class PlayerPlatform(StrEnum):
    """Players platforms"""

    CONSOLE = "console"
    PC = "pc"


class CompetitiveDivision(StrEnum):
    """Competitive division of a rank"""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    MASTER = "master"
    GRANDMASTER = "grandmaster"
    ULTIMATE = "ultimate"


class PlayerRegion(StrEnum):
    EUROPE = "europe"
    AMERICAS = "americas"
    ASIA = "asia"


# ULTIMATE competitive division doesn't exists in hero stats endpoint
CompetitiveDivisionFilter = StrEnum(
    "CompetitiveDivisionFilter",
    {tier.name: tier.value for tier in CompetitiveDivision if tier.name != "ULTIMATE"},
)
CompetitiveDivisionFilter.__doc__ = (
    "Competitive divisions ('grandmaster' includes 'champion')"
)
