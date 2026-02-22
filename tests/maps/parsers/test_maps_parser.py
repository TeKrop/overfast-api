from app.adapters.blizzard.parsers.maps import parse_maps_csv
from app.maps.enums import MapKey


def test_parse_maps_csv_returns_all_maps():
    result = parse_maps_csv()
    assert isinstance(result, list)
    assert len(result) > 0
    assert {m["key"] for m in result} == {str(m) for m in MapKey}


def test_parse_maps_csv_entry_format():
    result = parse_maps_csv()
    first = result[0]
    assert set(first.keys()) == {
        "key",
        "name",
        "screenshot",
        "gamemodes",
        "location",
        "country_code",
    }
    assert first["key"] == "aatlis"
    assert isinstance(first["gamemodes"], list)
