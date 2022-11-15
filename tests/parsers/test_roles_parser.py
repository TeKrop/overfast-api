from overfastapi.parsers.roles_parser import RolesParser


def test_roles_page_parsing(home_html_data: str, roles_json_data: list):
    parser = RolesParser(home_html_data)
    assert parser.hash == "ea153ae377336a868a705fa62b3e25cb"

    parser.parse()
    assert parser.data == roles_json_data
