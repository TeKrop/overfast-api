from app.domain.enums import MapKey
from app.domain.parsers.maps import filter_maps_by_gamemode, parse_maps_csv


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


# ── filter_maps_by_gamemode ───────────────────────────────────────────────────


def test_filter_maps_by_gamemode_none_returns_all():
    maps = [
        {"key": "a", "gamemodes": ["assault", "control"]},
        {"key": "b", "gamemodes": ["escort"]},
    ]
    actual = filter_maps_by_gamemode(maps, None)

    assert actual is maps


def test_filter_maps_by_gamemode_filters_correctly():
    maps = [
        {"key": "a", "gamemodes": ["assault", "control"]},
        {"key": "b", "gamemodes": ["escort"]},
        {"key": "c", "gamemodes": ["control"]},
    ]
    result = filter_maps_by_gamemode(maps, "control")

    assert [m["key"] for m in result] == ["a", "c"]


def test_filter_maps_by_gamemode_no_match_returns_empty():
    maps = [{"key": "a", "gamemodes": ["assault"]}]
    actual = filter_maps_by_gamemode(maps, "nonexistent")

    assert actual == []
