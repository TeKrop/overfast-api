"""Custom FastAPI response classes."""

import json

from fastapi.responses import JSONResponse


class ASCIIJSONResponse(JSONResponse):
    """JSONResponse that always produces ASCII-safe output."""

    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=True,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")
