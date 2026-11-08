"""Tests for app/api/docs.py — render_documentation and setup_custom_openapi"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.docs import (
    OVERFAST_REDOC_SCRIPT,
    render_documentation,
    setup_custom_openapi,
)


class TestRenderDocumentation:
    def test_returns_html_response(self):
        resp = render_documentation(
            title="Test Title",
            favicon_url="/static/favicon.png",
            openapi_url="/openapi.json",
        )

        assert isinstance(resp, HTMLResponse)

    def test_title_appears_in_content(self):
        resp = render_documentation(
            title="My API Docs",
            favicon_url="/static/favicon.png",
            openapi_url="/openapi.json",
        )

        body = bytes(resp.body).decode()

        assert "My API Docs" in body

    def test_favicon_url_in_content(self):
        resp = render_documentation(
            title="T",
            favicon_url="/static/custom-favicon.ico",
            openapi_url="/openapi.json",
        )

        body = bytes(resp.body).decode()

        assert "/static/custom-favicon.ico" in body

    def test_openapi_url_in_content(self):
        resp = render_documentation(
            title="T",
            favicon_url="/f.png",
            openapi_url="/v2/openapi.json",
        )

        body = bytes(resp.body).decode()

        assert "/v2/openapi.json" in body

    def test_redoc_script_included(self):
        resp = render_documentation(
            title="T", favicon_url="/f.png", openapi_url="/o.json"
        )

        body = bytes(resp.body).decode()

        assert OVERFAST_REDOC_SCRIPT in body


class TestSetupCustomOpenapi:
    def _make_app(self) -> FastAPI:
        test_app = FastAPI(title="Test App", version="0.0.1")

        @test_app.get("/heroes")
        def get_heroes():
            return []

        return test_app

    def test_openapi_callable_is_set(self):
        test_app = self._make_app()
        setup_custom_openapi(test_app)

        assert callable(test_app.openapi)

    def test_logo_added_to_schema(self):
        test_app = self._make_app()
        setup_custom_openapi(test_app)
        schema = test_app.openapi()

        assert "x-logo" in schema["info"]
        assert schema["info"]["x-logo"]["altText"] == "OverFast API Logo"

    def test_schema_is_cached_on_second_call(self):
        test_app = self._make_app()
        setup_custom_openapi(test_app)
        schema1 = test_app.openapi()
        schema2 = test_app.openapi()

        assert schema1 is schema2  # Same object — cached

    def test_new_route_badge_added_when_path_exists(self):
        test_app = self._make_app()
        setup_custom_openapi(test_app, new_route_path="/heroes")
        schema = test_app.openapi()

        # Each HTTP method config under /heroes should have x-badges
        for method_config in schema["paths"]["/heroes"].values():
            assert "x-badges" in method_config
            assert method_config["x-badges"][0]["name"] == "NEW"

    def test_new_route_badge_skipped_when_path_missing(self):
        test_app = self._make_app()
        # Non-existent path — should not crash
        setup_custom_openapi(test_app, new_route_path="/does-not-exist")
        schema = test_app.openapi()

        # /heroes should not have a badge
        for method_config in schema["paths"].get("/heroes", {}).values():
            assert "x-badges" not in method_config

    def test_no_new_route_path_no_badges(self):
        test_app = self._make_app()
        setup_custom_openapi(test_app, new_route_path=None)
        schema = test_app.openapi()

        for path_config in schema["paths"].values():
            for method_config in path_config.values():
                assert "x-badges" not in method_config
