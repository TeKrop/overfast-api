from unittest.mock import Mock, patch

from overfastapi.parsers.roles_parser import RolesParser


def test_roles_page_parsing(home_html_data: str, roles_json_data: list):
    parser = RolesParser()

    with patch(
        "requests.get",
        return_value=Mock(status_code=200, text=home_html_data),
    ):
        parser.parse()

    assert parser.data == roles_json_data
