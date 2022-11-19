import re
from unittest.mock import Mock, patch

import pytest

from overfastapi.common.exceptions import ParserInitError, ParserParsingError
from overfastapi.parsers.player_parser import PlayerParser


@pytest.mark.parametrize(
    "player_id,player_hash,search_account_response,player_html_data,player_json_data",
    [
        (
            "Ka1zen_x",
            "5cc2e2a3206ca8eddb6056fbcd041801",
            [
                {"urlName": "Ka1zen_x"},
                {"urlName": "Fake-1234"},
            ],
            "Ka1zen_x",
            "Ka1zen_x",
        ),
        (
            "mightyy_Brig",
            "23e4a18016ac56dc159a8fd834e553e8",
            [
                {"urlName": "mightyy_Brig"},
                {"urlName": "Fake-1234"},
            ],
            "mightyy_Brig",
            "mightyy_Brig",
        ),
        (
            "test-e66c388f13a7f408a6e1738f3d5161e2",
            "edc1a1fc08736118389d1031f0b3ca21",
            [
                {"urlName": "test-e66c388f13a7f408a6e1738f3d5161e2"},
                {"urlName": "Fake-1234"},
            ],
            "test-e66c388f13a7f408a6e1738f3d5161e2",
            "test-e66c388f13a7f408a6e1738f3d5161e2",
        ),
        (
            "xJaymog",
            "dd0708fd1d19598bbe45d6a51a9f18cc",
            [
                {"urlName": "xJaymog"},
                {"urlName": "Fake-1234"},
            ],
            "xJaymog",
            "xJaymog",
        ),
        (
            "TeKrop-2217",
            "743cc42856803dd6d80dc4bbdf2abf8e",
            [
                {"urlName": "TeKrop-2217"},
                {"urlName": "Fake-1234"},
            ],
            "TeKrop-2217",
            "TeKrop-2217",
        ),
        (
            "Player-162460",
            "bbef09ed7797bc823f21b3ba4946d310",
            [
                {"urlName": "Player-162460"},
                {"urlName": "Fake-1234"},
            ],
            "Player-162460",
            "Player-162460",
        ),
        (
            "test-1337",
            "a83f993b680fc4a4868b1cc9e8b9c51c",
            [
                {"urlName": "test-1337"},
                {"urlName": "Fake-1234"},
            ],
            "test-1337",
            "test-1337",
        ),
        (
            "test-325d682072d7a4c61c33b6bbaa83b859",
            "892a1c1763afb5c0998f0632cfa2ae74",
            [
                {"urlName": "test-325d682072d7a4c61c33b6bbaa83b859"},
                {"urlName": "Fake-1234"},
            ],
            "test-325d682072d7a4c61c33b6bbaa83b859",
            "test-325d682072d7a4c61c33b6bbaa83b859",
        ),
    ],
    indirect=["player_html_data", "player_json_data"],
)
def test_player_page_parsing(
    player_id: str,
    player_hash: str,
    search_account_response: list[dict],
    player_html_data: str,
    player_json_data: dict,
):
    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=player_html_data),
    ):
        parser = PlayerParser(player_id=player_id)
    assert parser.hash == player_hash

    with patch(
        "requests.get",
        Mock(return_value=Mock(status_code=200, json=lambda: search_account_response)),
    ):
        parser.parse()
        assert parser.data == player_json_data


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
def test_unknown_player_parser_init_error(player_html_data: str):
    with pytest.raises(ParserInitError):
        with patch(
            "requests.get",
            return_value=Mock(status_code=200, text=player_html_data),
        ):
            PlayerParser(player_id="Unknown-1234")


@patch(
    "requests.get",
    Mock(
        return_value=Mock(
            status_code=200,
            json=lambda: [{"urlName": "TeKrop-2217"}],
        )
    ),
)
@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_player_parser_parsing_error(player_html_data: str):
    # TODO : refacto
    # AttributeError
    with pytest.raises(ParserParsingError) as error:
        player_attr_error = player_html_data.replace(
            'class="masthead-player"', 'class="blabla"'
        )
        parser = PlayerParser(player_attr_error, player_id="TeKrop-2217")
        parser.parse()
    assert (
        error.value.message
        == "AttributeError(\"'NoneType' object has no attribute 'find'\")"
    )

    # KeyError
    with pytest.raises(ParserParsingError) as error:
        player_key_error = re.sub(
            'class="player-portrait" src="[^"]*"',
            'class="player-portrait"',
            player_html_data,
        )
        parser = PlayerParser(player_key_error, player_id="TeKrop-2217")
        parser.parse()
    assert error.value.message == "KeyError('src')"

    # IndexError
    with pytest.raises(ParserParsingError) as error:
        player_index_error = player_html_data.replace(
            '"/career/pc/TeKrop-2217/"', '"career"'
        )
        parser = PlayerParser(player_index_error, player_id="TeKrop-2217")
        parser.parse()
    assert error.value.message == "IndexError('list index out of range')"

    # TypeError
    with pytest.raises(ParserParsingError) as error:
        player_type_error = player_html_data.replace('class="player-portrait"', "")
        parser = PlayerParser(player_type_error, player_id="TeKrop-2217")
        parser.parse()
    assert (
        error.value.message == "TypeError(\"'NoneType' object is not subscriptable\")"
    )
