from unittest.mock import MagicMock, patch

import pytest

from app.heroes.controllers.get_hero_controller import GetHeroController


@pytest.fixture(scope="package")
def get_hero_controller() -> GetHeroController:
    with patch(
        "app.controllers.AbstractController.__init__", MagicMock(return_value=None)
    ):
        return GetHeroController()
