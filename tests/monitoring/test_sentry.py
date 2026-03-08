"""Tests for monitoring/sentry.py — setup_sentry initialisation"""

import sys
from unittest.mock import MagicMock, patch

from app.monitoring.sentry import setup_sentry


class TestSetupSentry:
    def test_setup_sentry_no_dsn_does_nothing(self):
        """When sentry_dsn is empty/None, sentry_sdk.init is never called."""
        with patch("app.monitoring.sentry.settings") as mock_settings:
            mock_settings.sentry_dsn = None
            # sentry_sdk should not even be imported — certainly not called
            with patch.dict("sys.modules", {"sentry_sdk": MagicMock()}):
                spy = MagicMock()
                sys.modules["sentry_sdk"] = spy
                setup_sentry()
                spy.init.assert_not_called()

    def test_setup_sentry_with_dsn_calls_init(self):
        """When sentry_dsn is set, sentry_sdk.init is called with dsn and release."""
        mock_sentry = MagicMock()
        with (
            patch("app.monitoring.sentry.settings") as mock_settings,
            patch.dict("sys.modules", {"sentry_sdk": mock_sentry}),
        ):
            mock_settings.sentry_dsn = "https://fake@sentry.io/123"
            mock_settings.app_version = "1.2.3"
            setup_sentry()

        mock_sentry.init.assert_called_once()
        call_kwargs = mock_sentry.init.call_args.kwargs
        assert call_kwargs["dsn"] == "https://fake@sentry.io/123"
        assert call_kwargs["release"] == "1.2.3"
        assert call_kwargs["send_default_pii"] is True
