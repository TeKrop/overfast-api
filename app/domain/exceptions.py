"""Set of custom exceptions used in the API"""

from fastapi import status


class RateLimitedError(Exception):
    """Raised when Blizzard is actively rate-limiting us (throttle penalty period).

    ``retry_after`` is the number of seconds until the penalty expires.
    """

    def __init__(self, retry_after: int = 0):
        super().__init__()
        self.retry_after = retry_after
        self.message = f"Blizzard rate limited — retry after {retry_after}s"

    def __str__(self) -> str:
        return self.message


class OverfastError(Exception):
    """Generic OverFast API Exception"""

    message = "OverFast API Error"

    def __str__(self):
        return self.message


class ParserBlizzardError(OverfastError):
    """Exception raised when there was an error in a Parser class
    initialization, usually when the data is not available
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Parser Blizzard Error"

    def __init__(self, status_code: int, message: str):
        super().__init__()
        self.status_code = status_code
        self.message = message


class ParserParsingError(OverfastError):
    """Exception raised when there was an error during data parsing"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Parser Parsing Error"

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class SearchDataRetrievalError(OverfastError):
    """Generic search data retrieval Exception (namecards, titles, etc.)"""

    message = "Error while retrieving search data"
