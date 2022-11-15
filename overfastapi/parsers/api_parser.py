"""Abstract API Parser module"""
from abc import ABC, abstractmethod
from functools import cached_property
from hashlib import md5

from bs4 import BeautifulSoup

from overfastapi.common.exceptions import ParserParsingError


class APIParser(ABC):
    """Abstract Parser class used to define generic behavior for parsers"""

    def __init__(self, html_content: str, **kwargs):
        self.root_tag = BeautifulSoup(html_content, "lxml").body.find(
            **self.root_tag_params
        )
        # Attribute containing parsed data
        self.data = None

    @cached_property
    def hash(self) -> str:
        """Returns an MD5 hash of the input data, used for caching"""
        return md5(str(self.root_tag).encode("utf-8")).hexdigest()

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
        try:
            self.data = self.parse_data()
        except (AttributeError, KeyError, IndexError, TypeError) as error:
            raise ParserParsingError(repr(error)) from error

    @abstractmethod
    def parse_data(self) -> dict | list:
        """Main submethod of the parser, mainly doing the parsing of input data and
        returning a dict, which will be cached and used by the API. Can
        raise an error if there is an issue when parsing the data.
        """
