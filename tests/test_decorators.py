from time import sleep
from unittest.mock import Mock, patch

from app.decorators import rate_limited
from app.logging import logger


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
    with patch("app.logging.logger.info", logger_info_mock):
        # Call the method with same parameters a third time,
        # it should work fine for the next one shouldn't
        method_to_limit(param1=42, param2="test", param3=True)
        logger_info_mock.assert_called()

    logger_info_mock = Mock()
    with patch("app.logging.logger.info", logger_info_mock):
        # Now call the method again, it should reach the limit and not being called
        method_to_limit(param1=42, param2="test", param3=True)
        logger_info_mock.assert_not_called()

        # Try to call with others parameters, it should work
        method_to_limit(param1=3, param2="test", param3=True)
        logger_info_mock.assert_called()

    # Now sleep during interval duration and try again, it should work again
    sleep(2)

    logger_info_mock = Mock()
    with patch("app.logging.logger.info", logger_info_mock):
        method_to_limit(param1=42, param2="test", param3=True)
        logger_info_mock.assert_called()
