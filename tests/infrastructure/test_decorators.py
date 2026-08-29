from time import sleep
from unittest.mock import Mock, patch

from app.infrastructure.decorators import rate_limited
from app.infrastructure.logger import logger


def test_rate_limited():
    # Define the rate limited method
    @rate_limited(max_calls=3, interval=2)
    def method_to_limit(param1: int, param2: str, param3: bool):
        logger.info(
            "Here is the method to limit with %d, %s, %s",
            param1,
            param2,
            param3,
        )

    # Call the method with same parameters twice
    method_to_limit(param1=42, param2="test", param3=True)
    method_to_limit(param1=42, param2="test", param3=True)

    logger_info_mock = Mock()
    with patch("app.infrastructure.logger.logger.info", logger_info_mock):
        # Call the method with same parameters a third time,
        # it should work fine for the next one shouldn't
        method_to_limit(param1=42, param2="test", param3=True)
        logger_info_mock.assert_called()

    logger_info_mock = Mock()
    with patch("app.infrastructure.logger.logger.info", logger_info_mock):
        # Now call the method again, it should reach the limit and not being called
        method_to_limit(param1=42, param2="test", param3=True)
        logger_info_mock.assert_not_called()

        # Try to call with others parameters, it should work
        method_to_limit(param1=3, param2="test", param3=True)
        logger_info_mock.assert_called()

    # Now sleep during interval duration and try again, it should work again
    sleep(2)

    logger_info_mock = Mock()
    with patch("app.infrastructure.logger.logger.info", logger_info_mock):
        method_to_limit(param1=42, param2="test", param3=True)
        logger_info_mock.assert_called()


def test_rate_limited_does_not_leak_keys():
    """Expired entries must be dropped, not just their timestamps.

    The cache key embeds the call arguments, and the real caller
    (send_discord_webhook_message) passes the error text in `fields`, so a
    distinct traceback produced a permanent entry. Trimming only the
    timestamp list inside a key left the key itself behind forever — an
    unbounded dict on the error path, where volume spikes.
    """

    @rate_limited(max_calls=1, interval=1)
    def method_to_limit(payload: str):
        return payload

    # Each call carries a unique payload, mimicking distinct tracebacks.
    distinct_errors = 50
    for i in range(distinct_errors):
        method_to_limit(payload=f"error-{i}")

    # Reach the decorator's call_history through the wrapper's closure.
    call_history = next(
        cell.cell_contents
        for cell in method_to_limit.__closure__
        if isinstance(cell.cell_contents, dict)
    )
    assert len(call_history) == distinct_errors, (
        "sanity: every key is still live inside the window"
    )

    sleep(1.1)
    method_to_limit(payload="error-final")

    # One call after the window expires must collapse all the earlier keys.
    assert len(call_history) == 1, (
        f"expired keys were not dropped: {len(call_history)} entries remain"
    )
