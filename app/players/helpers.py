import re
import unicodedata
from functools import cache

from app.helpers import read_csv_data_file
from app.roles.enums import Role

from .enums import CompetitiveDivision, CompetitiveRole, HeroKey

DURATION_HOURS_PATTERN = re.compile(r"^(-?\d+,?\d*?):(\d+):(\d+)$")
DURATION_MINUTES_PATTERN = re.compile(r"^(-?\d+):(\d+)$")
INT_PATTERN = re.compile(r"^-?\d+(,\d+)*%?$")
FLOAT_PATTERN = re.compile(r"^-?\d+(,\d+)*\.\d+$")


@cache
def get_hero_name(hero_key: HeroKey) -> str:  # ty: ignore[invalid-type-form]
    """Get a hero name based on the CSV file"""
    heroes_data = read_csv_data_file("heroes")
    return next(
        (
            hero_data["name"]
            for hero_data in heroes_data
            if hero_data["key"] == hero_key
        ),
        hero_key,
    )


def key_to_label(key: str) -> str:
    """Transform a given key in lowercase format into a human format"""
    return " ".join(s.capitalize() for s in key.split("_"))


def get_player_title(title: dict | str | None) -> str | None:
    """
    Get player title from string or dict extracted from Blizzard API.
    Handles:
      - None or empty string: returns None
      - String "No Title" (case-insensitive): returns None
      - Dict: returns 'en_US' value or None if not found
    """
    if not title:
        return None

    if isinstance(title, str):
        return None if title.lower() == "no title" else title

    if isinstance(title, dict):
        return title.get("en_US") or None

    return None


def get_computed_stat_value(input_str: str) -> str | float | int:
    """Get computed value from player statistics : convert duration representations
    into seconds (int), percentages into int, cast integer and float strings into
    int and float respectively.
    """

    # Duration format in hour:min:sec => seconds
    if result := DURATION_HOURS_PATTERN.match(input_str):
        return (
            int(result[1].replace(",", "")) * 3600
            + int(result[2]) * 60
            + int(result[3])
        )

    # Duration format in min:sec => seconds
    if result := DURATION_MINUTES_PATTERN.match(input_str):
        return int(result[1]) * 60 + int(result[2])

    # Int format
    if INT_PATTERN.match(input_str):
        return int(input_str.replace("%", "").replace(",", ""))

    # Float format
    if FLOAT_PATTERN.match(input_str):
        return float(input_str.replace(",", ""))

    # Return 0 value if :
    # - Zero time fought with a character ("--")
    # - Invalid value in DOM ("NaN")
    # Else default value
    return 0 if input_str in {"--", "NaN"} else input_str


def get_division_from_icon(rank_url: str) -> CompetitiveDivision:
    division_name = rank_url.split("/")[-1].split("-")[0].split("_")[-1]
    return CompetitiveDivision(division_name[:-4].lower())


def get_endorsement_value_from_frame(frame_url: str) -> int:
    """Extracts the endorsement level from the frame URL. 0 if not found."""
    try:
        return int(frame_url.split("/")[-1].split("-")[0])
    except ValueError:
        return 0


@cache
def get_hero_keyname(input_str: str) -> str:
    """Returns Overwatch hero keyname using its fullname.
    Example : ("Soldier: 76" -> "soldier-76")
    """
    input_str = input_str.replace(".", "").replace(":", "")
    return string_to_snakecase(input_str).replace("_", "-")


def get_role_key_from_icon(icon_url: str) -> CompetitiveRole:  # ty: ignore[invalid-type-form]
    """Extract role key from the role icon."""
    icon_role_key = icon_url.split("/")[-1].split("-")[0].upper()
    return (
        CompetitiveRole.DAMAGE  # ty: ignore[unresolved-attribute]
        if icon_role_key == "OFFENSE"
        else CompetitiveRole[icon_role_key]  # ty: ignore[invalid-argument-type]
    )


def get_stats_hero_class(hero_class: str | None) -> str:
    """Extract the specific classname from the classes list for a given hero."""
    if not hero_class:
        return ""

    start_index = hero_class.find("option-")
    end_index = start_index + len("option-")
    while end_index < len(hero_class) and hero_class[end_index].isdigit():
        end_index += 1
    return hero_class[start_index:end_index]


def get_tier_from_icon(tier_url: str | None) -> int:
    """Extracts the rank tier from the rank URL. 0 if not found."""
    if not tier_url:
        return 0

    try:
        return int(tier_url.split("/")[-1].split("-")[0].split("_")[-1])
    except (IndexError, ValueError):
        return 0


@cache
def string_to_snakecase(input_str: str) -> str:
    """Returns a string transformed in snakecase format"""
    cleaned_str = remove_accents(input_str).replace("- ", "")
    return (
        re.sub(r"(?<=[a-z])(?=[A-Z])|[^a-zA-Z0-9]", "_", cleaned_str).strip("_").lower()
    )


@cache
def remove_accents(input_str: str) -> str:
    """Removes accents from a string and return the resulting string"""
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


@cache
def get_hero_role(hero_key: HeroKey) -> Role:  # ty: ignore[invalid-type-form]
    """Get the role of a given hero based on the CSV file"""
    heroes_data = read_csv_data_file("heroes")
    role_key = next(
        hero_data["role"] for hero_data in heroes_data if hero_data["key"] == hero_key
    )
    return Role(role_key)


@cache
def get_real_category_name(category_name: str) -> str:
    """Specific method used because Blizzard sometimes name their categories
    in singular or plural. Example : "Objective Kill" or "Objective Kills".
    For consistency, I forced categories in one form (plural).

    Also handles localized category names from non-English profiles.
    """
    category_names_mapping = {
        "Game Won": "Games Won",
        "Elimination per Life": "Eliminations per Life",
        "Objective Kill": "Objective Kills",
    }
    return category_names_mapping.get(category_name, category_name)


@cache
def normalize_career_stat_category_name(category_label: str) -> str:
    """Normalize localized career stat category names to English.

    Blizzard returns category names in the user's language, but we need
    to normalize them to English for our API enum validation.

    Args:
        category_label: The category label extracted from Blizzard HTML (may be localized)

    Returns:
        English category name
    """
    # Lowercase for case-insensitive matching
    category_lower = category_label.lower()

    # Localization mappings for career stat categories
    localization_map = {
        # Portuguese
        "assistências": "Assists",
        "média": "Average",
        "melhor": "Best",
        "jogo": "Game",
        "para cada herói": "Hero Specific",
        "prêmios de partida": "Match Awards",
        "diversos": "Miscellaneous",
        # Spanish (combate same as Portuguese)
        "asistencias": "Assists",
        "promedio": "Average",
        "mejor": "Best",
        "combate": "Combat",
        "juego": "Game",
        "específico del héroe": "Hero Specific",
        "premios de partida": "Match Awards",
        "varios": "Miscellaneous",
        # French
        "assistances": "Assists",
        "moyenne": "Average",
        "meilleur": "Best",
        "combat": "Combat",
        "jeu": "Game",
        "spécifique au héros": "Hero Specific",
        "récompenses de match": "Match Awards",
        "divers": "Miscellaneous",
        # German
        "assists": "Assists",
        "durchschnitt": "Average",
        "bester wert": "Best",
        "kampf": "Combat",
        "spiel": "Game",
        "heldenspezifisch": "Hero Specific",
        "match-auszeichnungen": "Match Awards",
        "verschiedenes": "Miscellaneous",
        # Italian
        "assistenze": "Assists",
        "media": "Average",
        "migliore": "Best",
        "combattimento": "Combat",
        "partita": "Game",
        "specifico dell'eroe": "Hero Specific",
        "premi partita": "Match Awards",
        "varie": "Miscellaneous",
        # Japanese
        "アシスト": "Assists",
        "ベスト": "Best",
        "戦闘": "Combat",
        "ゲーム": "Game",
        "ヒーロー特有": "Hero Specific",
        "試合の報酬": "Match Awards",
        "その他": "Miscellaneous",
        # Korean
        "지원": "Assists",
        "평균": "Average",
        "최고 기록": "Best",
        "전투": "Combat",
        "게임": "Game",
        "영웅별": "Hero Specific",
        "경기 포상": "Match Awards",
        "기타": "Miscellaneous",
        # Chinese Simplified
        "助攻": "Assists",
        "最佳": "Best",
        "战斗": "Combat",
        "比赛": "Game",
        "英雄特有": "Hero Specific",
        "比赛奖励": "Match Awards",
        "综合": "Miscellaneous",
        # Chinese Traditional (different characters)
        "戰鬥": "Combat",
        "遊戲": "Game",
        "英雄專屬": "Hero Specific",
        "比賽獎勵": "Match Awards",
        "綜合": "Miscellaneous",
        # Russian
        "помощь": "Assists",
        "среднее": "Average",
        "лучшее": "Best",
        "бой": "Combat",
        "игра": "Game",
        "уникальное для героя": "Hero Specific",
        "награды матча": "Match Awards",
        "разное": "Miscellaneous",
        # Polish
        "asysty": "Assists",
        "średnia": "Average",
        "najlepszy wynik": "Best",
        "walka": "Combat",
        "gra": "Game",
        "dla bohatera": "Hero Specific",
        "nagrody meczowe": "Match Awards",
        "różne": "Miscellaneous",
    }

    # Try to find a match
    normalized = localization_map.get(category_lower)
    if normalized:
        return normalized

    # If no localization match found, return original
    # (handles English and any future languages)
    return category_label


@cache
def get_plural_stat_key(stat_key: str) -> str:
    """Specific method used because Blizzard sometimes name their stats
    in singular or plural, like the category names. Example : "Game Played"
    or "Game Played". For consistency, I forced stats in one form (plural).
    """
    general_game_keys = {
        "game_lost": "games_lost",
        "game_played": "games_played",
        "game_won": "games_won",
        "hero_win": "hero_wins",
        "card": "cards",
    }

    variable_stats_keys = {
        # General
        "assist": "assists",
        "critical_hit": "critical_hits",
        "critical_hit_kill": "critical_hit_kills",
        "death": "deaths",
        "defensive_assist": "defensive_assists",
        "elimination": "eliminations",
        "environmental_kill": "environmental_kills",
        "final_blow": "final_blows",
        "long_range_final_blow": "long_range_final_blows",
        "melee_final_blow": "melee_final_blows",
        "melee_kill": "melee_kills",
        "multikill": "multikills",
        "objective_kill": "objective_kills",
        "offensive_assist": "offensive_assists",
        "player_knocked_back": "players_knocked_back",
        "recon_assist": "recon_assists",
        "solo_kill": "solo_kills",
        "scoped_critical_hit": "scoped_critical_hits",
        # Ana
        "enemy_slept": "enemies_slept",
        "biotic_grenade_kill": "biotic_grenade_kills",
        "nano_boost_assist": "nano_boost_assists",
        # Ashe
        "bob_kill": "bob_kills",
        "coach_gun_kill": "coach_gun_kills",
        "dynamite_kill": "dynamite_kills",
        # Baptiste
        "amplification_matrix_assist": "amplification_matrix_assists",
        "immortality_field_death_prevented": "immortality_field_deaths_prevented",
        # Bastion
        "assault_kill": "assault_kills",
        "recon_kill": "recon_kills",
        "tactical_grenade_kill": "tactical_grenade_kills",
        "tank_kill": "tank_kills",
        # Brigitte
        "whipshot_attempted": "whipshots_attempted",
        # Cassidy
        "deadeye_kill": "deadeye_kills",
        "fan_the_hammer_kill": "fan_the_hammer_kills",
        "magnetic_grenade_kill": "magnetic_grenade_kills",
        # D.Va
        "call_mech_kill": "call_mech_kills",
        "micro_missile_kill": "micro_missile_kills",
        "self_destruct_kill": "self_destruct_kills",
        # Doomfist
        "meteor_strike_kill": "meteor_strike_kills",
        # Echo
        "focusing_beam_kill": "focusing_beam_kills",
        "sticky_bombs_direct_hit": "sticky_bombs_direct_hits",
        "sticky_bombs_kill": "sticky_bombs_kills",
        # Genji
        "dragonblade_kill": "dragonblade_kills",
        # Hanzo
        "dragonstrike_kill": "dragonstrike_kills",
        "storm_arrow_kill": "storm_arrow_kills",
        # Junker Queen
        "carnage_kill": "carnage_kills",
        "jagged_blade_kill": "jagged_blade_kills",
        "rampage_kill": "rampage_kills",
        # Junkrat
        "concussion_mine_kill": "concussion_mine_kills",
        "enemy_trapped": "enemies_trapped",
        "rip_tire_kill": "rip_tire_kills",
        # Kiriko
        "kitsune_rush_assist": "kitsune_rush_assists",
        "kunai_kill": "kunai_kills",
        "negative_effect_cleansed": "negative_effects_cleansed",
        # Lifeweaver
        "thorn_volley_kill": "thorn_volley_kills",
        "life_grip_death_prevented": "life_grip_deaths_prevented",
        # Lùcio
        "sound_barrier_provided": "sound_barriers_provided",
        # Mei
        "blizzard_kill": "blizzard_kills",
        "enemy_frozen": "enemies_frozen",
        # Mercy
        "blaster_kill": "blaster_kills",
        "player_resurrected": "players_resurrected",
        # Moira
        "biotic_orb_kill": "biotic_orb_kills",
        "coalescence_kill": "coalescence_kills",
        # Orisa
        "energy_javelin_kill": "energy_javelin_kills",
        "javelin_spin_kill": "javelin_spin_kills",
        "terra_surge_kill": "terra_surge_kills",
        # Pharah
        "barrage_kill": "barrage_kills",
        "rocket_direct_hit": "rocket_direct_hits",
        # Ramattra
        "annihilation_kill": "annihilation_kills",
        "pummel_kill": "pummel_kills",
        "ravenous_vortex_kill": "ravenous_vortex_kills",
        # Reaper
        "death_blossom_kill": "death_blossom_kills",
        # Reinhardt
        "charge_kill": "charge_kills",
        "earthshatter_kill": "earthshatter_kills",
        "fire_strike_kill": "fire_strike_kills",
        # Roadhog
        "chain_hook_kill": "chain_hook_kills",
        "whole_hog_kill": "whole_hog_kills",
        # Sigma
        "accretion_kill": "accretion_kills",
        "gravitic_flux_kill": "gravitic_flux_kills",
        # Sojourn
        "charged_shot_kill": "charged_shot_kills",
        "disruptor_shot_kill": "disruptor_shot_kills",
        "overclock_kill": "overclock_kills",
        # Soldier-76
        "helix_rocket_kill": "helix_rocket_kills",
        "tactical_visor_kill": "tactical_visor_kills",
        # Sombra
        "enemy_hacked": "enemies_hacked",
        "low_health_teleport": "low_health_teleports",
        # Symmetra
        "player_teleported": "players_teleported",
        "sentry_turret_kill": "sentry_turret_kills",
        # Torbjorn
        "molten_core_kill": "molten_core_kills",
        "overload_kill": "overload_kills",
        "turret_kill": "turret_kills",
        # Tracer
        "low_health_recall": "low_health_recalls",
        "pulse_bomb_attached": "pulse_bombs_attached",
        "pulse_bomb_kill": "pulse_bomb_kills",
        # Widowmaker
        "venom_mine_kill": "venom_mine_kills",
        # Winston
        "jump_kill": "jump_kills",
        "jump_pack_kill": "jump_pack_kills",
        "primal_rage_kill": "primal_rage_kills",
        "weapon_kill": "weapon_kills",
        # Wrecking Ball
        "grappling_claw_kill": "grappling_claw_kills",
        "minefield_kill": "minefield_kills",
        "piledriver_kill": "piledriver_kills",
        # Zarya
        "graviton_surge_kill": "graviton_surge_kills",
        "high_energy_kill": "high_energy_kills",
        # Zenyatta
        "charged_volley_kill": "charged_volley_kills",
    }

    stat_keys_suffixes = {"avg_per_10_min", "most_in_game", "most_in_life"}

    stat_keys_mapping = {
        **general_game_keys,
        **variable_stats_keys,
        **{
            f"{single_stat_key}_{suffix}": f"{plural_stat_key}_{suffix}"
            for single_stat_key, plural_stat_key in variable_stats_keys.items()
            for suffix in stat_keys_suffixes
        },
    }

    return stat_keys_mapping.get(stat_key, stat_key)
