"""Set of custom exceptions used in the API"""
from fastapi import status


class OverfastError(Exception):
    """Generic OverFast API Exception"""

    message = "OverFast API Error"

    def __str__(self):
        return self.message


class ParserInitError(OverfastError):
    """Exception raised when there was an error in a Parser class
    initialization, usually when the data is not available
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Parser Init Error"

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
