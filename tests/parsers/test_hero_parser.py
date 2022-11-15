import pytest

from overfastapi.parsers.hero_parser import HeroParser


@pytest.mark.parametrize(
    "hero_hash,hero_html_data,hero_json_data",
    [
        ("efb81d6e2b0b9f1eb7e8667446fc44b1", "ana", "ana"),
        ("f5790fa54f18cd89f98a5546ec16a63a", "ashe", "ashe"),
        ("0538b357136684dac2f64f752b456561", "baptiste", "baptiste"),
        ("3abf4169b7ad8e5fcc6a996d580b3756", "bastion", "bastion"),
        ("1e470c9a0aeac20826c59c5a9de54580", "brigitte", "brigitte"),
        ("fd53c7e72044042b01c5952a586aed16", "cassidy", "cassidy"),
        ("cef7ba36dd22e4bbf0bd27514fee364e", "dva", "dva"),
        ("51c19c15d0ff5423e2a94e5193a25090", "doomfist", "doomfist"),
        ("e5ba0405018a823cd7468635ec6b3167", "echo", "echo"),
        ("087365b1c807b4f968632556fe7dd56a", "genji", "genji"),
        ("ab3b2cb65335c4668ed2560391696dae", "hanzo", "hanzo"),
        ("7980caf6d366fae5c899c2cceb16d179", "junker-queen", "junker-queen"),
        ("29c908e79d85edade64e55e7e6e21713", "junkrat", "junkrat"),
        ("851bde2b76f2dfe672aab3c8f103e92e", "kiriko", "kiriko"),
        ("2df325751be4d70989700a71f09b1318", "lucio", "lucio"),
        ("3c865bb0ced855c21a3e603fda096a44", "mei", "mei"),
        ("713c19782072a9edf8b48a0ee547a9c9", "mercy", "mercy"),
        ("17e34f1ba73724d8e37e8b2bb682e6cf", "moira", "moira"),
        ("b3336358a66ecca5d628137182b00a47", "orisa", "orisa"),
        ("e678a011093c2915f2f0982dbc2a67b9", "pharah", "pharah"),
        ("248a88c4295880617602eee2dc58f970", "reaper", "reaper"),
        ("9a52bbc87559f3145c8a18a4ca72cb3e", "reinhardt", "reinhardt"),
        ("961cb4248d27eadb43b19bf93c319983", "roadhog", "roadhog"),
        ("3f00f91d5a90789a0a35d7e9a8863561", "sigma", "sigma"),
        ("5312260df23d965bf8ee5624fe63e9f2", "sojourn", "sojourn"),
        ("c215d512d3b462053df6346b4510cea3", "soldier-76", "soldier-76"),
        ("d4a47391b15248db05b967de25c9563b", "sombra", "sombra"),
        ("eb9933af47c11f9950f8f841214d6817", "symmetra", "symmetra"),
        ("badace5f6530612852291b996a3bd6b7", "torbjorn", "torbjorn"),
        ("e11bc0c610702ddc9ef5db1824730d14", "tracer", "tracer"),
        ("71619970c0a0ee3ff7926f2a367388e5", "widowmaker", "widowmaker"),
        ("a13e918bfe0508e8e046740fa2055638", "winston", "winston"),
        ("d1274f8643e6f87b82d1072b354fac72", "wrecking-ball", "wrecking-ball"),
        ("7cd7c708b0294a238a78ce5464f810a5", "zarya", "zarya"),
        ("8b13c6f4ecb58891936664c5c35b623d", "zenyatta", "zenyatta"),
    ],
    indirect=["hero_html_data", "hero_json_data"],
)
def test_hero_page_parsing(hero_hash: str, hero_html_data: str, hero_json_data: dict):
    parser = HeroParser(hero_html_data)
    assert parser.hash == hero_hash

    parser.parse()
    assert parser.data == hero_json_data
