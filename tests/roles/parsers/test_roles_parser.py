from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.adapters.blizzard.parsers.roles import fetch_roles_html, parse_roles_html
from app.overfast_client import OverFastClient
from app.roles.enums import Role


def test_parse_roles_html_returns_all_roles(home_html_data: str):
    result = parse_roles_html(home_html_data)
    assert isinstance(result, list)
    assert {role["key"] for role in result} == {r.value for r in Role}


def test_parse_roles_html_entry_format(home_html_data: str):
    result = parse_roles_html(home_html_data)
    first = result[0]
    assert set(first.keys()) == {"key", "name", "icon", "description"}


@pytest.mark.asyncio
async def test_fetch_roles_html_calls_blizzard(home_html_data: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=home_html_data),
    ):
        client = OverFastClient()
        html = await fetch_roles_html(client)

    assert html == home_html_data
