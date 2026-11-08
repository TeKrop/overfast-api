"""Custom FastAPI response classes."""

import json
from typing import Any, override

from fastapi.responses import JSONResponse


class ASCIIJSONResponse(JSONResponse):
    """JSONResponse that always produces ASCII-safe output."""

    @override
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=True,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")
