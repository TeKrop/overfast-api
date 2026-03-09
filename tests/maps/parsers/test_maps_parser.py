from app.domain.enums import MapKey
from app.domain.parsers.maps import filter_maps_by_gamemode, parse_maps, parse_maps_csv


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


# ── parse_maps ────────────────────────────────────────────────────────────────


def test_parse_maps_without_gamemode_returns_all():
    result = parse_maps()

    assert len(result) == len(parse_maps_csv())


def test_parse_maps_with_gamemode_returns_subset():
    all_maps = parse_maps_csv()
    # Pick a gamemode that actually exists in the data
    some_gamemode = all_maps[0]["gamemodes"][0]
    filtered = parse_maps(gamemode=some_gamemode)

    assert len(filtered) <= len(all_maps)
    assert all(some_gamemode in m["gamemodes"] for m in filtered)
