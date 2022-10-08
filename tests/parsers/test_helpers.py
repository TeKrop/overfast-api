# pylint: disable=C0114,C0116
import pytest

from overfastapi.config import BLIZZARD_HOST
from overfastapi.parsers.helpers import get_full_url


@pytest.mark.parametrize(
    "url,full_url",
    [
        (
            "https://www.youtube.com/watch?v=yzFWIw7wV8Q",
            "https://www.youtube.com/watch?v=yzFWIw7wV8Q",
        ),
        ("/media/stories/bastet", f"{BLIZZARD_HOST}/media/stories/bastet"),
    ],
)
def test_get_full_url(url: str, full_url: str):
    assert get_full_url(url) == full_url
