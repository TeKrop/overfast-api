import pytest

from app import helpers


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
    assert helpers.get_human_readable_duration(input_duration) == result
