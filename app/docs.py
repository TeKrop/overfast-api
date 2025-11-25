import json

from fastapi.responses import HTMLResponse

OVERFAST_REDOC_THEME = {
    "spacing": {"sectionVertical": 32, "sectionHorizontal": 28},
    "typography": {
        "fontFamily": "Roboto, 'Segoe UI', Arial, sans-serif",
        "fontSize": "16px",
        "fontWeightBold": "600",
        "headings": {"fontWeight": "700", "lineHeight": "1.25"},
        "code": {"fontFamily": "'Fira Code', Consolas, monospace"},
    },
    "colors": {
        "primary": {"main": "#ff9c00", "light": "#ffd37a"},
        "success": {"main": "#1fb8ff"},
        "text": {
            "primary": "#f4f5f7",
            "secondary": "#cfd3dc",
            "light": "#94a2c3",
        },
        "http": {
            "get": "#1fb8ff",
            "post": "#ff9c00",
            "delete": "#ff5f56",
            "put": "#33c38c",
            "patch": "#b58bff",
        },
        "responses": {
            "success": {"color": "#1fb8ff"},
            "info": {"color": "#b58bff"},
            "redirect": {"color": "#ffd37a"},
            "clientError": {"color": "#ff5f56"},
            "serverError": {"color": "#ff4081"},
        },
        "menu": {"backgroundColor": "rgba(5, 8, 15, 0.85)", "textColor": "#f4f5f7"},
        "rightPanel": {"backgroundColor": "rgba(8, 11, 18, 0.9)"},
    },
    "menu": {
        "backgroundColor": "rgba(5, 8, 15, 0.6)",
        "textColor": "#d8deed",
        "groupItems": {
            "activeTextColor": "#ff9c00",
            "activeArrowColor": "#ff9c00",
            "textTransform": "uppercase",
        },
        "level1Items": {"textTransform": "uppercase"},
    },
    "rightPanel": {"backgroundColor": "rgba(5, 8, 15, 0.65)"},
}

OVERFAST_REDOC_SCRIPT = "https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js"


def render_documentation(
    *,
    title: str,
    favicon_url: str,
    openapi_url: str,
) -> HTMLResponse:
    """Render the Overwatch-themed Redoc page."""

    redoc_options = {"theme": OVERFAST_REDOC_THEME, "hideLoading": True}
    options_json = json.dumps(redoc_options)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{title}</title>
        <link rel="icon" type="image/png" href="{favicon_url}" />
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@500&family=Roboto" rel="stylesheet">
        <link rel="stylesheet" href="/static/overwatch-redoc.css" />
      </head>
      <body>
        <noscript>
          ReDoc requires Javascript to function. Please enable it to browse the documentation.
        </noscript>
        <div id="overfast-loader"></div>
        <div id="redoc-container"></div>
        <script src="{OVERFAST_REDOC_SCRIPT}"></script>
        <script>
          Redoc.init(
            "{openapi_url}",
            {options_json},
            document.getElementById("redoc-container"),
            () => document.getElementById('overfast-loader').remove()
          );
        </script>
      </body>
    </html>
    """

    return HTMLResponse(content=html_content)
