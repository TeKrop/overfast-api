from unittest.mock import Mock, patch

import pytest

from app.common.enums import Role
from app.common.exceptions import OverfastError
from app.common.helpers import overfast_client
from app.parsers.roles_parser import RolesParser


@pytest.mark.asyncio
async def test_roles_page_parsing(home_html_data: str):
    parser = RolesParser()

    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=home_html_data),
    ):
        try:
            await parser.parse()
        except OverfastError:
            pytest.fail("Roles list parsing failed")

    assert {role["key"] for role in parser.data} == {r.value for r in Role}
