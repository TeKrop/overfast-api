"""Abstract API Parser module"""

from abc import ABC, abstractmethod
from functools import cached_property

from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.logging import logger


class AbstractParser(ABC):
    """Abstract Parser class used to define generic behavior for parsers.

    A parser is meant to convert some input data into meaningful data
    in dict/list format. The Parse Cache system is handled here.
    """

    cache_manager = CacheManager()

    def __init__(self, **kwargs):
        self.data = None

    @property
    @abstractmethod
    def timeout(self) -> int:
        """Timeout used for Parser Cache storage for this specific parser"""

    @cached_property
    def cache_key(self) -> str:
        """Key used for caching using Parser Cache"""
        return type(self).__name__

    @abstractmethod
    async def retrieve_and_parse_data(self) -> None:
        """Method used to retrieve data, parsing it and
        storing it into self.data attribute.
        """

    async def parse(self) -> None:
        """Main parsing method, first checking if there is any Parser Cache. If
        not, it's calling the main submethod to retrieve and parse data.
        """
        logger.info("Checking Parser Cache...")
        parser_cache = self.cache_manager.get_parser_cache(self.cache_key)
        if parser_cache is not None:
            # Parser cache is here
            logger.info("Parser Cache found !")
            self.data = parser_cache
            return

        # No cache is available, it's the first time the user requested the
        # data or the Parser Cache has expired : retrieve and parse data (
        # Blizzard page for API Parser or local file for others parsers)
        await self.retrieve_and_parse_data()

    def filter_request_using_query(self, **kwargs) -> dict | list:
        """If the route contains subroutes accessible using GET queries, this method
        will filter data using the query data. This method should be
        redefined in child classes if needed. The default behaviour is to return
        the parsed data directly.
        """
        return self.data
