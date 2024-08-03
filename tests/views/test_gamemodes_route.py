from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient

from app.config import settings


@pytest.mark.asyncio()
async def test_get_gamemodes(client: AsyncClient):
    response = await client.get("/gamemodes")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


@pytest.mark.asyncio()
async def test_get_gamemodes_internal_error(client: AsyncClient):
    with patch(
        "app.handlers.list_gamemodes_request_handler."
        "ListGamemodesRequestHandler.process_request",
        return_value=[{"invalid_key": "invalid_value"}],
    ):
        response = await client.get("/gamemodes")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"error": settings.internal_server_error_message}
