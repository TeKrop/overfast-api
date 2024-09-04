from unittest.mock import Mock, patch

import httpx
import pytest

from app.common.enums import Role
from app.common.exceptions import OverfastError
from app.parsers.roles_parser import RolesParser


@pytest.mark.asyncio
async def test_roles_page_parsing(home_html_data: str):
    client = httpx.AsyncClient()
    parser = RolesParser(client=client)

    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=200, text=home_html_data),
    ):
        try:
            await parser.parse()
        except OverfastError:
            pytest.fail("Roles list parsing failed")
        finally:
            await client.aclose()

    assert {role["key"] for role in parser.data} == {r.value for r in Role}
