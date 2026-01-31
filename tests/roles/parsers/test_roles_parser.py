from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from fastapi import status

from app.exceptions import OverfastError
from app.roles.enums import Role

if TYPE_CHECKING:
    from app.roles.parsers.roles_parser import RolesParser


@pytest.mark.asyncio
async def test_roles_page_parsing(roles_parser: RolesParser, home_html_data: str):
    with patch(
        "httpx.AsyncClient.get",
        return_value=Mock(status_code=status.HTTP_200_OK, text=home_html_data),
    ):
        try:
            await roles_parser.parse()
        except OverfastError:
            pytest.fail("Roles list parsing failed")

    assert isinstance(roles_parser.data, list)
    assert {role["key"] for role in roles_parser.data} == {r.value for r in Role}
