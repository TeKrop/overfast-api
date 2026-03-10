"""Set of custom exceptions used in the API"""

from http import HTTPStatus


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

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
    message = "OverFast API Error"

    def __str__(self):
        return self.message


class ParserBlizzardError(OverfastError):
    """Exception raised when there was an error in a Parser class
    initialization, usually when the data is not available
    """

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
    message = "Parser Blizzard Error"

    def __init__(self, status_code: int, message: str):
        super().__init__()
        self.status_code = status_code
        self.message = message


class ParserParsingError(OverfastError):
    """Exception raised when there was an error during data parsing"""

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
    message = "Parser Parsing Error"

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class ParserInternalError(OverfastError):
    """Raised by domain services when an unexpected parsing failure occurs.

    Carries the ``blizzard_url`` that was being parsed and the underlying
    ``cause`` so the API layer can call ``overfast_internal_error`` and send
    an alert without the domain needing to know about FastAPI or Discord.
    """

    message = "Internal Server Error"

    def __init__(self, blizzard_url: str, cause: Exception):
        super().__init__()
        self.blizzard_url = blizzard_url
        self.cause = cause


class SearchDataRetrievalError(OverfastError):
    """Generic search data retrieval Exception (namecards, titles, etc.)"""

    message = "Error while retrieving search data"
