# pylint: disable=C0114,C0116
import pytest

from overfastapi.parsers.hero_parser import HeroParser


@pytest.mark.parametrize(
    "hero_hash,hero_html_data,hero_json_data",
    [
        ("6a805b216d23ae029c5a9101eff1b87f", "ana", "ana"),
        ("7363efd0d179e152b2a4bf59825b1910", "ashe", "ashe"),
        ("903e32e7d74c2cbba9e5fff1e29bcfca", "baptiste", "baptiste"),
        ("3b388eda0aba64cc9ab3bc4ecda73a22", "bastion", "bastion"),
        ("229b1067a341928f87e042a16b28f0ce", "brigitte", "brigitte"),
        ("3201926b7c37fc866c9fe1bb13629205", "cassidy", "cassidy"),
        ("1dbb823ea2103b3eaca3493396da105f", "dva", "dva"),
        ("a5fcd75dd846a26e112241c30a68bbbb", "doomfist", "doomfist"),
        ("04bfe9582e1feda61f0076e34204fd36", "echo", "echo"),
        ("2700028820bb09d091be23b14a55277e", "genji", "genji"),
        ("f40d14d112063de744d6dfb9f89c30a6", "hanzo", "hanzo"),
        ("337e400219dda74cbc908b552e4aebee", "junkrat", "junkrat"),
        ("8b0fb868d4eed3672abe9da02a66486b", "lucio", "lucio"),
        ("72f456cd9ad8c0d4bb0c344556c621b7", "mei", "mei"),
        ("c075d984f149da715365cfacd5538400", "mercy", "mercy"),
        ("9dd47f124d3fb3be64f36e8706bff3bb", "moira", "moira"),
        ("2f72e25599155f344e410d2fb2ce1513", "orisa", "orisa"),
        ("1968ae0f302e82e49a23eff81cd16a0a", "pharah", "pharah"),
        ("25071adaf3bce42e3c64510712584d89", "reaper", "reaper"),
        ("ef5336af7929403d09e71aa7dd14cdf9", "reinhardt", "reinhardt"),
        ("8c90fd3460c5606a2026beca68c33295", "roadhog", "roadhog"),
        ("922a143e472c3118c8370f38d656a0d2", "sigma", "sigma"),
        ("3b93f32d9a970be54aa71c57f2570622", "soldier-76", "soldier-76"),
        ("e293c411734ce27f81392e13de3bc789", "sombra", "sombra"),
        ("679a4319410f3120e97bb30cd870b4a3", "symmetra", "symmetra"),
        ("c35e83dcde38d9625864787383e8d7fc", "torbjorn", "torbjorn"),
        ("e0033101e054c471d7e67f9dec7f8ab8", "tracer", "tracer"),
        ("c1f0c24936f92348953a95a00627ef0a", "widowmaker", "widowmaker"),
        ("727009b01b983c7e0145eb3ca3e6be05", "winston", "winston"),
        ("8d94c3af7c94bc7d2eb13345e2cbfebe", "wrecking-ball", "wrecking-ball"),
        ("5c4dbf3e049af2a0ac58dc260b15b564", "zarya", "zarya"),
        ("2dc3d21ea9a8f87ac453a6aeee0fde7d", "zenyatta", "zenyatta"),
    ],
    indirect=["hero_html_data", "hero_json_data"],
)
def test_hero_page_parsing(hero_hash: str, hero_html_data: str, hero_json_data: dict):
    parser = HeroParser(hero_html_data)
    assert parser.hash == hero_hash

    parser.parse()
    assert parser.data == hero_json_data
