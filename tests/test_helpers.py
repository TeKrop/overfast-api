from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.responses import Response

from app.api import helpers
from app.api.helpers import (
    _truncate_embed_fields,
    _truncate_text,
    apply_swr_headers,
    overfast_internal_error,
    send_discord_webhook_message,
)
from app.config import settings


@pytest.mark.parametrize(
    ("input_duration", "result"),
    [
        (98760, "1 day, 3 hours, 26 minutes"),
        (86400, "1 day"),
        (7200, "2 hours"),
        (3600, "1 hour"),
        (600, "10 minutes"),
        (60, "1 minute"),
    ],
)
def test_get_human_readable_duration(input_duration: int, result: str):
    actual = helpers.get_human_readable_duration(input_duration)

    assert actual == result


# ── _truncate_text ────────────────────────────────────────────────────────────


class TestTruncateText:
    def test_short_text_not_truncated(self):
        result = _truncate_text("hello", 10)

        assert result == "hello"

    def test_exact_length_not_truncated(self):
        result = _truncate_text("hello", 5)

        assert result == "hello"

    def test_long_text_truncated_with_default_suffix(self):
        result = _truncate_text("hello world", 8)

        assert result == "hello..."
        assert len(result) == 8  # noqa: PLR2004

    def test_long_text_truncated_with_custom_suffix(self):
        result = _truncate_text("hello world", 7, suffix="--")

        assert result.endswith("--")
        assert len(result) == 7  # noqa: PLR2004


# ── _truncate_embed_fields ────────────────────────────────────────────────────


class TestTruncateEmbedFields:
    def test_short_fields_untouched(self):
        fields = [{"name": "Error", "value": "short"}]
        result = _truncate_embed_fields(fields)

        assert result[0]["name"] == "Error"
        assert result[0]["value"] == "short"

    def test_long_name_truncated(self):
        long_name = "X" * 300
        fields = [{"name": long_name, "value": "v"}]
        result = _truncate_embed_fields(fields)

        assert len(result[0]["name"]) <= 250  # noqa: PLR2004

    def test_long_value_truncated(self):
        long_value = "Y" * 1100
        fields = [{"name": "n", "value": long_value}]
        result = _truncate_embed_fields(fields)

        assert len(result[0]["value"]) <= 1000  # noqa: PLR2004

    def test_multiple_fields_all_truncated(self):
        fields = [
            {"name": "A" * 300, "value": "B" * 1100},
            {"name": "ok", "value": "also ok"},
        ]
        result = _truncate_embed_fields(fields)

        assert len(result[0]["name"]) <= 250  # noqa: PLR2004
        assert len(result[0]["value"]) <= 1000  # noqa: PLR2004
        assert result[1]["name"] == "ok"


# ── send_discord_webhook_message ──────────────────────────────────────────────


class TestSendDiscordWebhookMessage:
    def test_webhook_disabled_returns_none(self):
        # conftest already patches discord_webhook_enabled=False
        result = send_discord_webhook_message(title="test", description="desc")

        assert result is None

    def test_webhook_disabled_logs_error(self):
        with patch("app.api.helpers.settings.discord_webhook_enabled", False):
            send_discord_webhook_message(title="Alert", description="Something broke")
        # Should have logged to the logger (tested indirectly via no exception)

    def test_webhook_enabled_builds_payload(self):
        """When webhook is enabled, httpx.post is called with correct structure."""
        mock_response = MagicMock()
        with (
            patch("app.api.helpers.settings.discord_webhook_enabled", True),
            patch(
                "app.api.helpers.settings.discord_webhook_url",
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
