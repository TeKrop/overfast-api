"""Abstract API Parser module"""
from abc import abstractmethod
from functools import cached_property
from typing import ClassVar

from bs4 import BeautifulSoup
from fastapi import status

from app.common.enums import Locale
from app.common.exceptions import ParserParsingError
from app.common.helpers import blizzard_response_error_from_request, overfast_request
from app.config import settings

from .abstract_parser import AbstractParser


class APIParser(AbstractParser):
    """Abstract API Parser class used to define generic behavior for parsers used
    to extract data from Blizzard HTML pages. The blizzard URL call is handled here.
    """

    # List of valid HTTP codes when retrieving Blizzard pages
    valid_http_codes: ClassVar[list] = [status.HTTP_200_OK]

    def __init__(self, **kwargs):
        self.blizzard_url = self.get_blizzard_url(**kwargs)
        super().__init__(**kwargs)

    @property
    @abstractmethod
    def root_path(self) -> str:
        """Root path of the Blizzard URL containing the data (/en-us/career/, etc."""

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

    async def retrieve_and_parse_data(self) -> None:
        """Method used to retrieve data from Blizzard (HTML data), parsing it
        and storing it into self.data attribute.
        """
        req = await overfast_request(self.blizzard_url)
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
        return f"{settings.blizzard_host}/{locale}{self.root_path}"
