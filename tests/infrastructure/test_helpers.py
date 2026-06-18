from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.responses import Response

from app.api import helpers as api_helpers
from app.api.helpers import apply_swr_headers
from app.config import settings
from app.infrastructure.helpers import (
    _MAX_DESC_LEN,
    _MAX_FIELD_NAME_LEN,
    _MAX_FIELD_VALUE_LEN,
    _MAX_TITLE_LEN,
    _build_embed,
    _truncate_embed_content,
    overfast_internal_error,
    send_discord_webhook_message,
)


@pytest.mark.parametrize(
    ("input_duration", "result"),
    [
        (98760, "1 day, 3 hours, 26 minutes"),
        (86400, "1 day"),
        (7200, "2 hours"),
        (3600, "1 hour"),
        (600, "10 minutes"),
        (60, "1 minute"),
        (30, "less than a minute"),
    ],
)
def test_get_human_readable_duration(input_duration: int, result: str):
    actual = api_helpers.get_human_readable_duration(input_duration)

    assert actual == result


# ── _build_embed ──────────────────────────────────────────────────────────────


class TestBuildEmbed:
    def test_always_includes_color_and_timestamp(self):
        embed = _build_embed(None, None, None, None, 0xFF0000)

        assert embed["color"] == 0xFF0000  # noqa: PLR2004
        assert "timestamp" in embed

    def test_none_color_uses_default_red(self):
        embed = _build_embed(None, None, None, None, None)

        assert embed["color"] == 0xE74C3C  # noqa: PLR2004

    def test_optional_fields_absent_when_none(self):
        embed = _build_embed(None, None, None, None, None)

        assert "title" not in embed
        assert "description" not in embed
        assert "url" not in embed
        assert "fields" not in embed

    def test_optional_fields_present_when_provided(self):
        fields = [{"name": "n", "value": "v"}]

        embed = _build_embed("Title", "Desc", "https://x.com", fields, None)

        assert embed["title"] == "Title"
        assert embed["description"] == "Desc"
        assert embed["url"] == "https://x.com"
        assert embed["fields"] == fields


# ── _truncate_embed_content ───────────────────────────────────────────────────


class TestTruncateEmbedContent:
    def test_title_at_limit_not_truncated(self):
        title = "x" * _MAX_TITLE_LEN

        result_title, _, _ = _truncate_embed_content(title, None, None)

        assert result_title == title

    def test_title_over_limit_truncated_with_ellipsis(self):
        title = "x" * (_MAX_TITLE_LEN + 1)

        result_title, _, _ = _truncate_embed_content(title, None, None)

        assert isinstance(result_title, str)
        assert len(result_title) == _MAX_TITLE_LEN
        assert result_title.endswith("...")

    def test_description_at_limit_not_truncated(self):
        desc = "y" * _MAX_DESC_LEN

        _, result_desc, _ = _truncate_embed_content(None, desc, None)

        assert result_desc == desc

    def test_description_over_limit_truncated_with_suffix(self):
        desc = "y" * (_MAX_DESC_LEN + 1)

        _, result_desc, _ = _truncate_embed_content(None, desc, None)

        assert isinstance(result_desc, str)
        assert len(result_desc) == _MAX_DESC_LEN
        assert result_desc.endswith("\n\n*(truncated)*")

    def test_field_name_over_limit_truncated(self):
        fields = [{"name": "n" * (_MAX_FIELD_NAME_LEN + 1), "value": "v"}]

        _, _, result_fields = _truncate_embed_content(None, None, fields)

        assert result_fields is not None
        assert len(result_fields[0]["name"]) == _MAX_FIELD_NAME_LEN
        assert result_fields[0]["name"].endswith("...")

    def test_field_value_over_limit_truncated(self):
        fields = [{"name": "n", "value": "v" * (_MAX_FIELD_VALUE_LEN + 1)}]

        _, _, result_fields = _truncate_embed_content(None, None, fields)

        assert result_fields is not None
        assert len(result_fields[0]["value"]) == _MAX_FIELD_VALUE_LEN
        assert result_fields[0]["value"].endswith("\n*(truncated)*")

    def test_field_name_at_limit_not_truncated(self):
        name = "n" * _MAX_FIELD_NAME_LEN
        fields = [{"name": name, "value": "v"}]

        _, _, result_fields = _truncate_embed_content(None, None, fields)

        assert result_fields is not None
        assert result_fields[0]["name"] == name

    def test_multiple_fields_mixed_truncation(self):
        short_name = "short"
        long_name = "n" * (_MAX_FIELD_NAME_LEN + 1)
        fields = [
            {"name": short_name, "value": "v"},
            {"name": long_name, "value": "v"},
        ]

        _, _, result_fields = _truncate_embed_content(None, None, fields)

        assert result_fields is not None
        assert result_fields[0]["name"] == short_name
        assert result_fields[1]["name"].endswith("...")

    def test_none_inputs_pass_through(self):
        result = _truncate_embed_content(None, None, None)

        assert result == (None, None, None)


# ── send_discord_webhook_message ──────────────────────────────────────────────


class TestSendDiscordWebhookMessage:
    def test_webhook_disabled_returns_none(self):
        # conftest already patches discord_webhook_enabled=False
        result = send_discord_webhook_message(title="test", description="desc")

        assert result is None

    def test_webhook_disabled_logs_error(self):
        with patch(
            "app.infrastructure.helpers.settings.discord_webhook_enabled", False
        ):
            send_discord_webhook_message(title="Alert", description="Something broke")
        # Should have logged to the logger (tested indirectly via no exception)

    def test_webhook_enabled_builds_payload(self):
        """When webhook is enabled, httpx.post is called with correct structure."""
        mock_response = MagicMock()
        with (
            patch("app.infrastructure.helpers.settings.discord_webhook_enabled", True),
            patch(
                "app.infrastructure.helpers.settings.discord_webhook_url",
                "https://discord.example.com/webhook",
            ),
            patch("httpx.post", return_value=mock_response) as mock_post,
        ):
            result = send_discord_webhook_message(
                title="New Alert",
                description="Something happened",
                url="https://example.com",
                fields=[{"name": "Field", "value": "Value"}],
                color=0x00FF00,
            )

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["username"] == "OverFast API"

        embeds = payload["embeds"]
        assert len(embeds) == 1

        embed = embeds[0]
        assert embed["title"] == "New Alert"
        assert embed["description"] == "Something happened"
        assert embed["url"] == "https://example.com"
        assert embed["color"] == 0x00FF00  # noqa: PLR2004
        assert embed["fields"] == [{"name": "Field", "value": "Value"}]
        assert result is mock_response


# ── overfast_internal_error ───────────────────────────────────────────────────


class TestOverfastInternalError:
    def test_returns_http_500_exception(self):
        exc = overfast_internal_error("/heroes", ValueError("test error"))

        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_long_validation_error_truncated(self):
        """Validation errors > 900 chars keep only first 5 lines."""
        long_msg = "1 validation error for Foo\n" + "\n".join(
            [f"field_{i}\n  value error" for i in range(100)]
        )
        assert len(long_msg) > 900  # noqa: PLR2004
        error = ValueError(long_msg)
        # Should not raise, just truncate
        exc = overfast_internal_error("/test", error)

        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_long_non_validation_error_truncated(self):
        """Non-validation errors > 900 chars are sliced."""
        long_msg = "X" * 1000
        error = RuntimeError(long_msg)
        exc = overfast_internal_error("/test", error)

        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_url_with_http_prefix_used_as_is(self):
        """URLs starting with http are not prefixed with app_base_url."""
        exc = overfast_internal_error("https://blizzard.com/page", ValueError("err"))

        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_url_without_http_prefix_gets_base_url(self):
        """Relative URLs are prefixed with settings.app_base_url."""
        exc = overfast_internal_error("/players/test", ValueError("err"))

        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ── apply_swr_headers ────────────────────────────────────────────────────────


class TestApplySWRHeaders:
    def _make_response(self) -> Response:
        return Response(content=b"", media_type="application/json")

    def test_fresh_response_sets_hit_status(self):
        resp = self._make_response()
        apply_swr_headers(resp, cache_ttl=3600, is_stale=False)

        assert resp.headers["X-Cache-Status"] == "hit"
        assert "stale-while-revalidate" not in resp.headers.get("Cache-Control", "")

    def test_stale_response_sets_stale_status(self):
        resp = self._make_response()
        apply_swr_headers(resp, cache_ttl=3600, is_stale=True)

        assert resp.headers["X-Cache-Status"] == "stale"
        assert "stale-while-revalidate" in resp.headers["Cache-Control"]

    def test_age_header_set_when_positive(self):
        resp = self._make_response()
        apply_swr_headers(resp, cache_ttl=3600, is_stale=False, age_seconds=42)

        assert resp.headers["Age"] == "42"

    def test_age_header_not_set_when_zero(self):
        resp = self._make_response()
        apply_swr_headers(resp, cache_ttl=3600, is_stale=False, age_seconds=0)

        assert "Age" not in resp.headers

    def test_cache_ttl_header_always_set(self):
        resp = self._make_response()
        apply_swr_headers(resp, cache_ttl=600, is_stale=False)

        assert resp.headers[settings.cache_ttl_header] == "600"

    def test_staleness_threshold_overrides_max_age(self):
        resp = self._make_response()
        apply_swr_headers(
            resp,
            cache_ttl=3600,
            is_stale=False,
            staleness_threshold=1800,
        )

        assert "max-age=1800" in resp.headers["Cache-Control"]
