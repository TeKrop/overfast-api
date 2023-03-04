import pytest

from overfastapi.common.enums import CompetitiveDivision, Role
from overfastapi.config import BLIZZARD_HOST
from overfastapi.parsers.helpers import (
    get_computed_stat_value,
    get_division_from_rank_icon,
    get_endorsement_value_from_frame,
    get_full_url,
    get_hero_keyname,
    get_role_key_from_icon,
    get_stats_hero_class,
    get_tier_from_rank_icon,
    remove_accents,
    string_to_snakecase,
)


@pytest.mark.parametrize(
    ("input_str", "result"),
    [
        # Time format in hour:min:sec => seconds
        ("1,448:50:56", 5215856),
        ("205:08:38", 738518),
        ("12:03:52", 43432),
        ("5:42:42", 20562),
        ("-0:00:00", 0),
        # Time format in min:sec => seconds
        ("11:40", 700),
        ("04:10", 250),
        ("07:55", 475),
        ("00:11", 11),
        ("-00:00", 0),
        # Int format
        ("0", 0),
        ("5", 5),
        ("-86", -86),
        ("46%", 46),
        ("208", 208),
        ("12585", 12585),
        ("68236356", 68236356),
        # Float format
        ("7.58", 7.58),
        ("37.89", 37.89),
        ("-86.96", -86.96),
        # Zero time fought with a character
        ("--", 0),
        # Default value for anything else
        ("string", "string"),
    ],
)
def test_get_computed_stat_value(input_str: str, result: int | float | str):
    assert get_computed_stat_value(input_str) == result


@pytest.mark.parametrize(
    ("rank_url", "division"),
    [
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/BronzeTier-4-6b6e7959d4.png",
            CompetitiveDivision.BRONZE,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/SilverTier-3-f8d27c0087.png",
            CompetitiveDivision.SILVER,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/GoldTier-4-14f100ffe2.png",
            CompetitiveDivision.GOLD,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/PlatinumTier-4-a34efd83ff.png",
            CompetitiveDivision.PLATINUM,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/DiamondTier-3-5808b1a384.png",
            CompetitiveDivision.DIAMOND,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/MasterTier-4-397f8722e0.png",
            CompetitiveDivision.MASTER,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/GrandmasterTier-3-e55e61f68f.png",
            CompetitiveDivision.GRANDMASTER,
        ),
    ],
)
def test_get_division_from_rank_icon(rank_url: str, division: CompetitiveDivision):
    assert get_division_from_rank_icon(rank_url) == division


@pytest.mark.parametrize(
    ("frame_url", "endorsement_value"),
    [
        (
            "https://static.playoverwatch.com/img/pages/career/icons/endorsement/0.svg#icon",
            0,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/endorsement/9de6d43ec5.svg",
            0,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/endorsement/1-9de6d43ec5.svg#icon",
            1,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/endorsement/2-8b9f0faa25.svg#icon",
            2,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/endorsement/3-8ccb5f0aef.svg#icon",
            3,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/endorsement/4-48261e1164.svg#icon",
            4,
        ),
    ],
)
def test_get_endorsement_value_from_frame(frame_url: str, endorsement_value: int):
    assert get_endorsement_value_from_frame(frame_url) == endorsement_value


@pytest.mark.parametrize(
    ("url", "full_url"),
    [
        (
            "https://www.youtube.com/watch?v=yzFWIw7wV8Q",
            "https://www.youtube.com/watch?v=yzFWIw7wV8Q",
        ),
        ("/media/stories/bastet", f"{BLIZZARD_HOST}/media/stories/bastet"),
    ],
)
def test_get_full_url(url: str, full_url: str):
    assert get_full_url(url) == full_url


@pytest.mark.parametrize(
    ("input_str", "result"),
    [
        ("Cassidy", "cassidy"),
        ("D.Va", "dva"),
        ("Doomfist", "doomfist"),
        ("Lúcio", "lucio"),
        ("Soldier: 76", "soldier-76"),
        ("Torbjörn", "torbjorn"),
        ("Widowmaker", "widowmaker"),
        ("Zenyatta", "zenyatta"),
        ("Wrecking Ball", "wrecking-ball"),
        ("Junker Queen", "junker-queen"),
    ],
)
def test_get_hero_keyname(input_str: str, result: str):
    assert get_hero_keyname(input_str) == result


@pytest.mark.parametrize(
    ("icon_url", "role"),
    [
        (
            "https://static.playoverwatch.com/img/pages/career/icons/role/offense-ab1756f419.svg#icon",
            Role.DAMAGE,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/role/tank-f64702b684.svg#icon",
            Role.TANK,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/role/support-0258e13d85.svg#icon",
            Role.SUPPORT,
        ),
    ],
)
def test_get_role_key_from_icon(icon_url: str, role: Role):
    assert get_role_key_from_icon(icon_url) == role


@pytest.mark.parametrize(
    ("hero_classes", "result"),
    [
        (["stats-container", "option-0", "is-active"], "option-0"),
        (["stats-container", "option-1"], "option-1"),
    ],
)
def test_get_stats_hero_class(hero_classes: list[str], result: str):
    assert get_stats_hero_class(hero_classes) == result


@pytest.mark.parametrize(
    ("rank_url", "tier"),
    [
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/PlatinumTier-2-2251fd0f3e.png",
            2,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/GrandmasterTier-3-e55e61f68f.png",
            3,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/BronzeTier-4-6b6e7959d4.png",
            4,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/6b6e7959d4.png",
            0,
        ),
    ],
)
def test_get_tier_from_rank_icon(rank_url: str, tier: int):
    assert get_tier_from_rank_icon(rank_url) == tier


@pytest.mark.parametrize(
    ("input_str", "result"),
    [
        ("test_string_without_accents", "test_string_without_accents"),
        ("ÀÁÂÃÄÅàáâãäå", "AAAAAAaaaaaa"),
        ("ÇÈÉÊËÌÍÎÏçèéêëìíîï", "CEEEEIIIIceeeeiiii"),
        ("ÑÒÓÔÕÖñòóôõö", "NOOOOOnooooo"),
        ("ÙÚÛÜÝùúûüý", "UUUUYuuuuy"),
        ("torbjörn", "torbjorn"),
        ("lúcio", "lucio"),
    ],
)
def test_remove_accents(input_str: str, result: str):
    assert remove_accents(input_str) == result


@pytest.mark.parametrize(
    ("input_str", "result"),
    [
        ("test_string", "test_string"),
        ("All Heroes", "all_heroes"),
        ("Super Long Sentence", "super_long_sentence"),
        ("Soldier 76", "soldier_76"),
        ("All Damage Done - Avg per 10 Min", "all_damage_done_avg_per_10_min"),
        ("Barrier Damage Done - Most in Game", "barrier_damage_done_most_in_game"),
        ("Teleporter Pads Destroyed", "teleporter_pads_destroyed"),
        ("Multikills", "multikills"),
        ("Hero Damage Done", "hero_damage_done"),
        ("Time Spent on Fire - Avg per 10 Min", "time_spent_on_fire_avg_per_10_min"),
    ],
)
def test_string_to_snakecase(input_str: str, result: str):
    assert string_to_snakecase(input_str) == result
