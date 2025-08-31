from abc import ABC, abstractmethod
from typing import ClassVar

import httpx
from fastapi import status
from selectolax.lexbor import LexborHTMLParser

from .cache_manager import CacheManager
from .config import settings
from .enums import Locale
from .exceptions import ParserParsingError
from .helpers import read_csv_data_file
from .overfast_client import OverFastClient
from .overfast_logger import logger


class AbstractParser(ABC):
    """Abstract Parser class used to define generic behavior for parsers.

    A parser is meant to convert some input data into meaningful data
    in dict/list format. The Parse Cache system is handled here.
    """

    cache_manager = CacheManager()

    def __init__(self, **_):
        self.data: dict | list | None = None

    @abstractmethod
    async def parse(self) -> None:
        """Method used to retrieve data, parsing it and
        storing it into self.data attribute.
        """

    def filter_request_using_query(self, **_) -> dict | list:
        """If the route contains subroutes accessible using GET queries, this method
        will filter data using the query data. This method should be
        redefined in child classes if needed. The default behaviour is to return
        the parsed data directly.
        """
        return self.data


class CSVParser(AbstractParser):
    """CSV Parser class used to define generic behavior for parsers used
    to extract data from local CSV files.
    """

    # Name of CSV file to retrieve (without extension), also
    # used as a sub-folder name for storing related static files
    filename: str

    async def parse(self) -> None:
        """Method used to retrieve data from CSV file and storing
        it into self.data attribute
        """

        # Read the CSV file
        self.csv_data = read_csv_data_file(self.filename)

        # Parse the data
        self.data = self.parse_data()

    @abstractmethod
    def parse_data(self) -> dict | list[dict]:
        """Main submethod of the parser, mainly doing the parsing of CSV data and
        returning a dict, which will be cached and used by the API. Can
        raise an error if there is an issue when parsing the data.
        """

    def get_static_url(self, key: str, extension: str = "jpg") -> str:
        """Method used to retrieve the URL of a local static file"""
        return f"{settings.app_base_url}/static/{self.filename}/{key}.{extension}"


class APIParser(AbstractParser):
    """Abstract API Parser class used to define generic behavior for parsers used
    to extract data from Blizzard HTML pages. The blizzard URL call is handled here.
    """

    # List of valid HTTP codes when retrieving Blizzard pages
    valid_http_codes: ClassVar[list] = [status.HTTP_200_OK]

    # Request headers to send while making the request
    request_headers: ClassVar[dict] = {}

    def __init__(self, **kwargs):
        self.blizzard_url = self.get_blizzard_url(**kwargs)
        self.blizzard_query_params = self.get_blizzard_query_params(**kwargs)
        self.overfast_client = OverFastClient()
        super().__init__(**kwargs)

    @property
    @abstractmethod
    def root_path(self) -> str:
        """Root path of the Blizzard URL containing the data (/en-us/career/, etc."""

    @abstractmethod
    def store_response_data(self, response: httpx.Response) -> None:
        """Submethod to handle response data storage"""

    @abstractmethod
    async def parse_data(self) -> dict | list[dict]:
        """Main submethod of the parser, mainly doing the parsing of input data and
        returning a dict, which will be cached and used by the API. Can
        raise an error if there is an issue when parsing the data.
        """

    async def parse(self) -> None:
        """Method used to retrieve data from Blizzard, parsing it
        and storing it into self.data attribute.
        """
        response = await self.overfast_client.get(
            url=self.blizzard_url,
            headers=self.request_headers,
            params=self.blizzard_query_params,
        )
        if response.status_code not in self.valid_http_codes:
            raise self.overfast_client.blizzard_response_error_from_response(response)

        # Store associated request data
        self.store_response_data(response)

        # Parse stored request data
        await self.parse_response_data()

    def get_blizzard_url(self, **kwargs) -> str:
        """URL used when requesting data to Blizzard. It usually is a concatenation
        of root url and query data (kwargs) if the Controller supports it.
        For example : single hero page (hero key), player career page
        (player id, etc.). Default is just the blizzard root url.
        """
        locale = kwargs.get("locale") or Locale.ENGLISH_US
        return f"{settings.blizzard_host}/{locale}{self.root_path}"

    def get_blizzard_query_params(self, **_) -> dict:
        """Query params to use when calling Blizzard URL. Defaults to empty dict"""
        return {}

    async def parse_response_data(self) -> None:
        logger.info("Parsing data...")
        try:
            self.data = await self.parse_data()
        except (AttributeError, KeyError, IndexError, TypeError) as error:
            raise ParserParsingError(repr(error)) from error


class HTMLParser(APIParser):
    request_headers: ClassVar[dict] = {"Accept": "text/html"}

    def store_response_data(self, response: httpx.Response) -> None:
        """Initialize parser tag with Blizzard response"""
        self.create_parser_tag(response.text)

    def create_parser_tag(self, html_content: str) -> None:
        self.root_tag = LexborHTMLParser(html_content).css_first(
            "div.main-content,main"
        )


class JSONParser(APIParser):
    request_headers: ClassVar[dict] = {"Accept": "application/json"}

    def store_response_data(self, response: httpx.Response) -> None:
        """Initialize object with Blizzard response"""
        self.json_data = response.json()
