from typing import Any

import pytest

from app.common import helpers


@pytest.mark.parametrize(
    ("input_dict", "key", "new_key", "new_value"),
    [
        # Empty dict
        ({}, "key", "new_key", "new_value"),
        # Key doesn't exist
        ({"key_one": 1, "key_two": 2}, "key", "new_key", "new_value"),
    ],
)
def test_dict_insert_value_before_key_with_key_error(
    input_dict: dict,
    key: str,
    new_key: str,
    new_value: Any,
):
    with pytest.raises(KeyError):
        helpers.dict_insert_value_before_key(input_dict, key, new_key, new_value)


@pytest.mark.parametrize(
    ("input_dict", "key", "new_key", "new_value", "result_dict"),
    [
        # Before first key
        (
            {"key_one": 1, "key_two": 2, "key_three": 3},
            "key_one",
            "key_four",
            4,
            {"key_four": 4, "key_one": 1, "key_two": 2, "key_three": 3},
        ),
        # Before middle key
        (
            {"key_one": 1, "key_two": 2, "key_three": 3},
            "key_two",
            "key_four",
            4,
            {"key_one": 1, "key_four": 4, "key_two": 2, "key_three": 3},
        ),
        # Before last key
        (
            {"key_one": 1, "key_two": 2, "key_three": 3},
            "key_three",
            "key_four",
            4,
            {"key_one": 1, "key_two": 2, "key_four": 4, "key_three": 3},
        ),
    ],
)
def test_dict_insert_value_before_key_valid(
    input_dict: dict,
    key: str,
    new_key: str,
    new_value: Any,
    result_dict: dict,
):
    assert (
        helpers.dict_insert_value_before_key(input_dict, key, new_key, new_value)
        == result_dict
    )


@pytest.mark.parametrize(
    ("key", "result_label"),
    [
        ("assists", "Assists"),
        ("hero_specific", "Hero Specific"),
        ("match_awards", "Match Awards"),
    ],
)
def test_key_to_label(key: str, result_label: str):
    assert helpers.key_to_label(key) == result_label


@pytest.mark.parametrize(
    ("title", "resulting_title"),
    [
        (None, None),
        ("No Title", None),
        ("Philosopher", "Philosopher"),
    ],
)
def test_get_player_title(title: str | None, resulting_title: str | None):
    assert helpers.get_player_title(title) == resulting_title
