"""Abstract API Parser module"""
import json
from abc import ABC, abstractmethod
from functools import cached_property
from hashlib import md5

from bs4 import BeautifulSoup

from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.exceptions import ParserParsingError
from overfastapi.common.helpers import blizzard_response_error, overfast_request
from overfastapi.common.logging import logger
from overfastapi.config import BLIZZARD_HOST


class APIParser(ABC):
    """Abstract Parser class used to define generic behavior for parsers.

    A parser is meant to convert Blizzard HTML page data into
    meaningful data in dict/list format. The blizzard URL
    call, and the API Cache system are handled here.
    """

    cache_manager = CacheManager()

    def __init__(self, **kwargs):
        self.blizzard_url = self.get_blizzard_url(**kwargs)

        # Retrieve the HTML content from the Blizzard page
        req = overfast_request(self.blizzard_url)
        if req.status_code != 200:
            raise blizzard_response_error(req)

        # Initialize BeautifulSoup object
        self.root_tag = BeautifulSoup(req.text, "lxml").body.find(
            **self.root_tag_params
        )
        # Attribute containing parsed data
        self.data = None

    @property
    @abstractmethod
    def root_path(self) -> str:
        """Root path of the Blizzard URL containing the data (/en-us/career/, etc."""

    @cached_property
    def hash(self) -> str:
        """Returns an MD5 hash of the input data, used for caching"""
        return md5(str(self.root_tag).encode("utf-8")).hexdigest()

    @cached_property
    def cache_key(self) -> str:
        """Key used for caching using Parser Cache. Blizzard URL is the default"""
        return self.blizzard_url

    @property
    def root_tag_params(self) -> dict:
        """Returns the BeautifulSoup params kwargs, used to find the root Tag
        on the page which will be used for searching and hashing (for cache). We
        don't want to calculate an hash and do the data parsing on all the HTML.
        """
        return {"name": "div", "class_": "main-content", "recursive": False}

    def parse(self) -> None:
        """Main parsing method, calling the main submethod and catching
        BeautifulSoup exceptions. If there is any, a ParserParsingError is raised.
        """

        # Check the Parser cache with received page calculated hash
        logger.info("Checking Parser Cache...")
        parser_cache_data = self.cache_manager.get_unchanged_parser_cache(
            self.cache_key, self.hash
        )
        if parser_cache_data:

            # Parser cache is already valid, no need to do anything
            logger.info("Parser Cache found !")
            self.data = json.loads(parser_cache_data)
            return

        # No cache is valid, we need to parse the data and update the cache
        logger.info("No valid Parser Cache found, parsing the page...")
        try:
            self.data = self.parse_data()
        except (AttributeError, KeyError, IndexError, TypeError) as error:
            raise ParserParsingError(repr(error)) from error

        # Update the Parser Cache
        dumped_parsed_data = json.dumps(self.data)
        self.cache_manager.update_parser_cache(
            self.cache_key, {"hash": self.hash, "data": dumped_parsed_data}
        )

    @abstractmethod
    def parse_data(self) -> dict | list:
        """Main submethod of the parser, mainly doing the parsing of input data and
        returning a dict, which will be cached and used by the API. Can
        raise an error if there is an issue when parsing the data.
        """

    @cached_property
    def blizzard_root_url(self) -> str:
        """Property containing Root URL for requesting data to Blizzard"""
        return f"{BLIZZARD_HOST}{self.root_path}"

    def get_blizzard_url(self, **kwargs) -> str:
        """URL used when requesting data to Blizzard. It usually is a concatenation
        of root url and query data (kwargs) if the RequestHandler supports it.
        For example : single hero page (hero key), player career page (platform and
        player id, etc.). Default is just the blizzard root url.
        """
        return self.blizzard_root_url

    def filter_request_using_query(self, **kwargs) -> dict | list:
        """If the route contains subroutes accessible using GET queries, this method
        will filter Blizzard data using the query data. This method should be
        redefined in child classes if needed. The default behaviour is to return
        the parsed data directly.
        """
        return self.data
