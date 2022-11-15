from overfastapi.parsers.heroes_parser import HeroesParser


def test_heroes_page_parsing(heroes_html_data: str, heroes_json_data: list):
    parser = HeroesParser(heroes_html_data)
    assert parser.hash == "ef946f23ec35caadf53cefc0ea812f25"

    parser.parse()
    assert parser.data == heroes_json_data
