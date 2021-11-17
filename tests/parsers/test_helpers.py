# pylint: disable=C0114,C0116
import pytest

from overfastapi.config import BLIZZARD_HOST
from overfastapi.parsers.helpers import (
    get_background_url_from_style,
    get_computed_stat_value,
    get_full_url,
    get_hero_keyname,
    remove_accents,
    string_to_snakecase,
)


@pytest.mark.parametrize(
    "style,url",
    [
        ("test_string", None),
        ("background-image:url( )", None),
        ("background-image:url()", None),
        ("background-image:https://url.com/test.jpg", None),
        ("background-image:url(https://url.com/test.jpg)", "https://url.com/test.jpg"),
        (
            (
                "background-image:url( https://d15f34w2p8l1cc.cloudfront.net/overwatch/"
                "ac14208753baf77110880020450fa4aa0121df0c344c32a2d20f77c18ba75db5.png )"
            ),
            (
                "https://d15f34w2p8l1cc.cloudfront.net/overwatch/ac14208753baf77110"
                "880020450fa4aa0121df0c344c32a2d20f77c18ba75db5.png"
            ),
        ),
    ],
)
def test_get_background_url_from_style(style: str, url: str | None):
    assert get_background_url_from_style(style) == url


@pytest.mark.parametrize(
    "url,full_url",
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
    "input_str,result",
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
    "input_str,result",
    [
        ("test_string", "test_string"),
        ("All Heroes", "all_heroes"),
        ("Super Long Sentence", "super_long_sentence"),
        ("Soldier 76", "soldier_76"),
        ("All Damage Done - Avg per 10 Min", "all_damage_done_avg_per_10_min"),
        ("Barrier Damage Done - Most in Game", "barrier_damage_done_most_in_game"),
        ("Teleporter Pads Destroyed", "teleporter_pads_destroyed"),
        ("Multikills", "multikills"),
        ("Medals - Gold", "medals_gold"),
        ("Time Spent on Fire - Avg per 10 Min", "time_spent_on_fire_avg_per_10_min"),
    ],
)
def test_string_to_snakecase(input_str: str, result: str):
    assert string_to_snakecase(input_str) == result


@pytest.mark.parametrize(
    "input_str,result",
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
    ],
)
def test_get_hero_keyname(input_str: str, result: str):
    assert get_hero_keyname(input_str) == result


@pytest.mark.parametrize(
    "input_str,result",
    [
        # Time format in hour:min:sec => seconds
        ("1,448:50:56", 5215856),
        ("205:08:38", 738518),
        ("12:03:52", 43432),
        ("5:42:42", 20562),
        # Time format in min:sec => seconds
        ("11:40", 700),
        ("04:10", 250),
        ("07:55", 475),
        ("00:11", 11),
        # Int format
        ("0", 0),
        ("5", 5),
        ("46%", 46),
        ("208", 208),
        ("12585", 12585),
        ("68236356", 68236356),
        # Float format
        ("7.58", 7.58),
        ("37.89", 37.89),
        # Zero time fought with a character
        ("--", 0),
        # Default value for anything else
        ("string", "string"),
    ],
)
def test_get_computed_stat_value(input_str: str, result: int | float | str):
    assert get_computed_stat_value(input_str) == result
