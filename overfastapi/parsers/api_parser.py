"""Abstract API Parser module"""
from abc import ABC, abstractmethod
from functools import cached_property

from bs4 import BeautifulSoup

from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.enums import Locale
from overfastapi.common.exceptions import ParserParsingError
from overfastapi.common.helpers import (
    blizzard_response_error_from_request,
    overfast_request,
)
from overfastapi.common.logging import logger
from overfastapi.config import BLIZZARD_HOST


class APIParser(ABC):
    """Abstract Parser class used to define generic behavior for parsers.

    A parser is meant to convert Blizzard HTML page data into
    meaningful data in dict/list format. The blizzard URL
    call, and the API Cache system are handled here.
    """

    cache_manager = CacheManager()

    # List of valid HTTP codes when retrieving Blizzard pages
    valid_http_codes = [200]

    def __init__(self, **kwargs):
        self.blizzard_url = self.get_blizzard_url(**kwargs)
        self.data = None

    @property
    @abstractmethod
    def root_path(self) -> str:
        """Root path of the Blizzard URL containing the data (/en-us/career/, etc."""

    @property
    @abstractmethod
    def timeout(self) -> int:
        """Timeout used for Parser Cache storage for this specific parser"""

    @cached_property
    def cache_key(self) -> str:
        """Key used for caching using Parser Cache. Blizzard URL
        concatenated with the Parser class name is the default.
        """
        return f"{type(self).__name__}-{self.blizzard_url}"

    @property
    def root_tag_params(self) -> dict:
        """Returns the BeautifulSoup params kwargs, used to find the root Tag
        on the page which will be used for searching and hashing (for cache). We
        don't want to calculate an hash and do the data parsing on all the HTML.
        """
        return {"name": "div", "class_": "main-content", "recursive": False}

    def parse(self) -> None:
        """Main parsing method, first checking if there is any Parser Cache. If
        not, it's calling the main submethod and catching BeautifulSoup exceptions.
        If there is any, a ParserParsingError is raised.
        """
        logger.info("Checking Parser Cache...")
        parser_cache = self.cache_manager.get_parser_cache(self.cache_key)
        if parser_cache is not None:
            # Parser cache is here
            logger.info("Parser Cache found !")
            self.data = parser_cache
            return

        # No cache is available, it's the first time the user requested the
        # data or the Parser Cache has expired : retrieve and parse Blizzard page
        self.retrieve_and_parse_blizzard_data()

    def retrieve_and_parse_blizzard_data(self) -> None:
        """Method used to retrieve data from Blizzard (HTML data), parsing it
        and storing it into self.data attribute.
        """
        req = overfast_request(self.blizzard_url)
        if req.status_code not in self.valid_http_codes:
            raise blizzard_response_error_from_request(req)

        # Initialize BeautifulSoup object
        self.root_tag = BeautifulSoup(req.text, "lxml").body.find(
            **self.root_tag_params
        )

        # Parse retrieved HTML data
        try:
            self.data = self.parse_data()
        except (AttributeError, KeyError, IndexError, TypeError) as error:
            raise ParserParsingError(repr(error)) from error

        # Update the Parser Cache
        self.cache_manager.update_parser_cache(self.cache_key, self.data, self.timeout)

    @abstractmethod
    def parse_data(self) -> dict | list[dict]:
        """Main submethod of the parser, mainly doing the parsing of input data and
        returning a dict, which will be cached and used by the API. Can
        raise an error if there is an issue when parsing the data.
        """

    def get_blizzard_url(self, **kwargs) -> str:
        """URL used when requesting data to Blizzard. It usually is a concatenation
        of root url and query data (kwargs) if the RequestHandler supports it.
        For example : single hero page (hero key), player career page
        (player id, etc.). Default is just the blizzard root url.
        """
        locale = kwargs.get("locale") or Locale.ENGLISH_US
        return f"{BLIZZARD_HOST}/{locale}{self.root_path}"

    def filter_request_using_query(self, **kwargs) -> dict | list:
        """If the route contains subroutes accessible using GET queries, this method
        will filter Blizzard data using the query data. This method should be
        redefined in child classes if needed. The default behaviour is to return
        the parsed data directly.
        """
        return self.data
