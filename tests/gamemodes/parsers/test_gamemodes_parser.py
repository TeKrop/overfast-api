from app.adapters.blizzard.parsers.gamemodes import parse_gamemodes_csv
from app.gamemodes.enums import MapGamemode


def test_parse_gamemodes_csv_returns_all_gamemodes():
    result = parse_gamemodes_csv()
    assert isinstance(result, list)
    assert len(result) > 0
    assert {g["key"] for g in result} == {str(g) for g in MapGamemode}


def test_parse_gamemodes_csv_entry_format():
    result = parse_gamemodes_csv()
    first = result[0]
    assert set(first.keys()) == {"key", "name", "icon", "description", "screenshot"}
    assert first["key"] == "assault"
