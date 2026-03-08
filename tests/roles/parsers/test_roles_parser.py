from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status

from app.adapters.blizzard import BlizzardClient
from app.domain.enums import Role
from app.domain.exceptions import ParserParsingError
from app.domain.parsers.roles import fetch_roles_html, parse_roles, parse_roles_html


def _wrap_in_main(inner_html: str) -> str:
    """Wrap HTML in the required main.main-content element so parse_html_root succeeds."""
    return f"<html><body><main class='main-content'>{inner_html}</main></body></html>"


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
        client = BlizzardClient()
        html = await fetch_roles_html(client)

    assert html == home_html_data


# ── parse_roles_html error paths ──────────────────────────────────────────────


def test_parse_roles_html_missing_container_raises():
    """No roles container → ParserParsingError."""
    html = _wrap_in_main("<div>No carousel here</div>")
    with pytest.raises(ParserParsingError):
        parse_roles_html(html)


def test_parse_roles_html_missing_tab_controls_raises():
    """Container present but no blz-tab-controls → ParserParsingError."""
    html = _wrap_in_main("""
      <div class="homepage-features-heroes">
        <blz-feature-carousel-section>
          <!-- no blz-tab-controls here -->
        </blz-feature-carousel-section>
      </div>
    """)
    with pytest.raises(ParserParsingError):
        parse_roles_html(html)


def test_parse_roles_html_missing_role_header_raises():
    """blz-feature without blz-header → ParserParsingError."""
    html = _wrap_in_main("""
      <div class="homepage-features-heroes">
        <blz-feature-carousel-section>
          <blz-tab-controls>
            <blz-tab-control><blz-image src="/icons/tank.png"></blz-image></blz-tab-control>
            <blz-tab-control><blz-image src="/icons/damage.png"></blz-image></blz-tab-control>
            <blz-tab-control><blz-image src="/icons/support.png"></blz-image></blz-tab-control>
          </blz-tab-controls>
          <blz-feature>
            <!-- no blz-header -->
          </blz-feature>
        </blz-feature-carousel-section>
      </div>
    """)
    with pytest.raises(ParserParsingError):
        parse_roles_html(html)


# ── parse_roles high-level ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_parse_roles_calls_fetch_and_parse(home_html_data: str):
    """parse_roles() calls fetch_roles_html then parse_roles_html."""
    mock_client = AsyncMock()
    with (
        patch(
            "app.domain.parsers.roles.fetch_roles_html",
            return_value=home_html_data,
        ) as mock_fetch,
        patch(
            "app.domain.parsers.roles.parse_roles_html",
            return_value=[{"key": "tank"}],
        ) as mock_parse,
    ):
        result = await parse_roles(mock_client)

    mock_fetch.assert_awaited_once()
    mock_parse.assert_called_once_with(home_html_data)

    assert result == [{"key": "tank"}]
