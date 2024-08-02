import pytest

from app.common.enums import CompetitiveDivision, CompetitiveRole, HeroKey, Locale
from app.config import settings
from app.parsers import helpers


@pytest.mark.parametrize(
    ("input_str", "result"),
    [
        # Time format in hour:min:sec => seconds
        ("1,448:50:56", 5_215_856),
        ("205:08:38", 738_518),
        ("12:03:52", 43_432),
        ("5:42:42", 20_562),
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
        ("12,585", 12_585),
        ("68,236,356", 68_236_356),
        # Float format
        ("7.58", 7.58),
        ("37.89", 37.89),
        ("-86.96", -86.96),
        ("1,102.5", 1_102.5),
        # Zero time fought with a character
        ("--", 0),
        # Invalid value (not a number)
        ("NaN", 0),
        # Default value for anything else
        ("string", "string"),
    ],
)
def test_get_computed_stat_value(input_str: str, result: float | str):
    assert helpers.get_computed_stat_value(input_str) == result


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
            "https://static.playoverwatch.com/img/pages/career/icons/rank/Rank_PlatinumTier-ccf57375a7.png",
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
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/Rank_UltimateTier-99f8248b65.png",
            CompetitiveDivision.ULTIMATE,
        ),
    ],
)
def test_get_division_from_icon(rank_url: str, division: CompetitiveDivision):
    assert helpers.get_division_from_icon(rank_url) == division


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
    assert helpers.get_endorsement_value_from_frame(frame_url) == endorsement_value


@pytest.mark.parametrize(
    ("url", "full_url"),
    [
        (
            "https://www.youtube.com/watch?v=yzFWIw7wV8Q",
            "https://www.youtube.com/watch?v=yzFWIw7wV8Q",
        ),
        ("/media/stories/bastet", f"{settings.blizzard_host}/media/stories/bastet"),
    ],
)
def test_get_full_url(url: str, full_url: str):
    assert helpers.get_full_url(url) == full_url


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
    assert helpers.get_hero_keyname(input_str) == result


@pytest.mark.parametrize(
    ("icon_url", "role"),
    [
        (
            "https://static.playoverwatch.com/img/pages/career/icons/role/offense-ab1756f419.svg#icon",
            CompetitiveRole.DAMAGE,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/role/tank-f64702b684.svg#icon",
            CompetitiveRole.TANK,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/role/support-0258e13d85.svg#icon",
            CompetitiveRole.SUPPORT,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/role/open-163b3b8ddc.svg#icon",
            CompetitiveRole.OPEN,
        ),
    ],
)
def test_get_role_key_from_icon(icon_url: str, role: CompetitiveRole):
    assert helpers.get_role_key_from_icon(icon_url) == role


@pytest.mark.parametrize(
    ("hero_classes", "result"),
    [
        (["stats-container", "option-0", "is-active"], "option-0"),
        (["stats-container", "option-1"], "option-1"),
    ],
)
def test_get_stats_hero_class(hero_classes: list[str], result: str):
    assert helpers.get_stats_hero_class(hero_classes) == result


@pytest.mark.parametrize(
    ("tier_url", "tier"),
    [
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/TierDivision_2-2251fd0f3e.png",
            2,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/TierDivision_3-1de89374e2.png",
            3,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/TierDivision_4-0cd0907e1b.png",
            4,
        ),
        (
            "https://static.playoverwatch.com/img/pages/career/icons/rank/6b6e7959d4.png",
            0,
        ),
    ],
)
def test_get_tier_from_icon(tier_url: str, tier: int):
    assert helpers.get_tier_from_icon(tier_url) == tier


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
    assert helpers.remove_accents(input_str) == result


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
    assert helpers.string_to_snakecase(input_str) == result


@pytest.mark.parametrize(("hero_key"), [(h.value) for h in HeroKey])
def test_get_hero_role(hero_key: HeroKey):
    try:
        helpers.get_hero_role(hero_key)
    except StopIteration:
        pytest.fail(f"Missing role for '{hero_key}' hero")


@pytest.mark.parametrize(
    ("input_str", "locale", "result"),
    [
        # Classic cases
        ("Aug 19 (Age: 37)", Locale.ENGLISH_US, ("Aug 19", 37)),
        ("May 9 (Age: 1)", Locale.ENGLISH_US, ("May 9", 1)),
        # Specific unknown case (bastion)
        ("Unknown (Age: 32)", Locale.ENGLISH_US, (None, 32)),
        # Specific venture case (not the same spacing)
        ("Aug 6 (Age : 26)", Locale.ENGLISH_US, ("Aug 6", 26)),
        ("Aug 6 (Age : 26)", Locale.ENGLISH_EU, ("Aug 6", 26)),
        # Other languages than english
        ("6. Aug. (Alter: 26)", Locale.GERMAN, ("6. Aug.", 26)),
        ("6 ago (Edad: 26)", Locale.SPANISH_EU, ("6 ago", 26)),
        ("6 ago (Edad: 26)", Locale.SPANISH_LATIN, ("6 ago", 26)),
        ("6 août (Âge : 26 ans)", Locale.FRENCH, ("6 août", 26)),
        ("6 ago (Età: 26)", Locale.ITALIANO, ("6 ago", 26)),
        ("8月6日 （年齢: 26）", Locale.JAPANESE, ("8月6日", 26)),
        ("8월 6일 (나이: 26세)", Locale.KOREAN, ("8월 6일", 26)),
        ("6 sie (Wiek: 26 lat)", Locale.POLISH, ("6 sie", 26)),
        ("6 de ago. (Idade: 26)", Locale.PORTUGUESE_BRAZIL, ("6 de ago.", 26)),
        ("6 авг. (Возраст: 26)", Locale.RUSSIAN, ("6 авг.", 26)),
        ("8月6日 （年齡：26）", Locale.CHINESE_TAIWAN, ("8月6日", 26)),
        # Invalid case
        ("Unknown", Locale.ENGLISH_US, (None, None)),
    ],
)
def test_get_birthday_and_age(
    input_str: str, locale: Locale, result: tuple[str | None, int | None]
):
    """Get birthday and age from text for a given hero"""
    assert helpers.get_birthday_and_age(input_str, locale) == result
