"""Abstract API Request Handler module"""
import json
from abc import ABC, abstractmethod

from fastapi import HTTPException, Request

from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.exceptions import ParserInitError, ParserParsingError
from overfastapi.common.helpers import overfast_internal_error
from overfastapi.common.logging import logger
from overfastapi.common.mixins import ApiRequestMixin
from overfastapi.parsers.api_parser import APIParser


class APIRequestHandler(ApiRequestMixin, ABC):
    """Generic abstract API Request Handler, containing attributes structure and methods
    in order to quickly be able to create concrete request handlers. A handler can
    be associated with several parsers (one parser = one Blizzard page parsing).
    The API Cache system is handled here.
    """

    # List of possible route filters for a given handler/route, used for API cache
    # update optimization. For example, let's say your calling the /heroes endpoint.
    # If an API cache update is required, it will be updated for the /heroes endpoint,
    # but also its subroutes using querystring : /heroes?role=damage, etc.
    route_filters = []

    # Generic cache manager class, used to manipulate Redis cache data
    cache_manager = CacheManager()

    def __init__(self, request: Request | None = None):
        self.cache_key = (
            CacheManager.get_cache_key_from_request(request) if request else None
        )

    @property
    @abstractmethod
    def api_root_url(self) -> str:
        """Root URL used for this specific handler (/players, /heroes, etc.)"""

    @property
    @abstractmethod
    def parser_classes(self) -> type:
        """Parser classes used for parsing the Blizzard page retrieved with this handler"""

    @property
    @abstractmethod
    def timeout(self) -> int:
        """Timeout used for API Cache storage for this specific handler"""

    def process_request(self, **kwargs) -> dict:
        """Main method used to process the request from user and return final data. Raises
        an HTTPException in case of error when retrieving or parsing data.

        The process uses API Cache if available and needed, the main steps are :
        - Check if API Cache data is here, and return it
        - Else, instanciate the dedicated parser classes, each one will :
            - Retrieve HTML data from Blizzard URL associated with the parser
            - Check if Parser Cache is available and up-to-date, return it
            - Else, parse the page completely, update the Parser Cache
        - Filter the data using kwargs parameters, then merge the data from parsers
        - Update related API Cache in background using parsers objects
        - Return the final data
        """

        # If we are using API Cache from inside the app
        # (no reverse proxy configured), check the API Cache
        if api_cache_data := self.get_api_cache_data():
            return api_cache_data

        # No API Cache or not using it in app, we request the data from Blizzard page
        logger.info("No API Cache, requesting the data to Blizzard...")
        parsers_data = []
        parsers = []
        for parser_class in self.parser_classes:
            # Instanciate the parser, it will retrieve its associated Blizzard
            # page and use the kwargs to generate the appropriate URL
            try:
                parser = parser_class(**kwargs)
            except ParserInitError as error:
                logger.error("Failed to instanciate Parser : {}", error.message)
                raise HTTPException(
                    status_code=error.status_code, detail=error.message
                ) from error
            except HTTPException:
                raise

            # Do the parsing. Internally, it will check for Parser Cache
            # before doing a real parsing using BeautifulSoup
            try:
                parser.parse()
            except ParserParsingError as error:
                raise overfast_internal_error(parser.blizzard_url, error) from error

            # Filter the data to obtain final parser data
            logger.info("Filtering the data using query...")
            parsers.append(parser)
            parsers_data.append(parser.filter_request_using_query(**kwargs))

        # Merge parsers data together
        computed_data = self.merge_parsers_data(parsers_data, **kwargs)

        # Do API cache updates in background
        logger.info("Updating related API Cache in background...")
        kwargs["background_tasks"].add_task(
            self.update_all_api_cache,
            parsers,
            **kwargs,
        )

        logger.info("Done ! Returning filtered data...")
        return computed_data

    def merge_parsers_data(
        self, parsers_data: list[dict | list], **kwargs
    ) -> dict | list:
        """Merge parsers data together. It depends on the given route and datas,
        and needs to be overriden in case a given Request Handler has several
        associated Parsers.
        """
        return parsers_data[0]

    def update_all_api_cache(self, parsers: list[APIParser], **kwargs) -> None:
        """Update all API Cache values concerning the given parser (if any)
        and the given kwargs (GET parameters on API request in general).

        The main steps of the process are :
        - If no parser was given, instanciate them using kwargs and parse the data
        - Update root path API Cache
        - Update subroutes API Caches. For example, for the player career
        route, it will update the cache for the summary route, stats, achivements, etc.
        """
        if not parsers:
            for parser_class in self.parser_classes:
                # Instanciate the parser, it will retrieve its associated Blizzard
                # page and use the kwargs to generate the appropriate URL
                try:
                    parser = parser_class(**kwargs)
                except HTTPException:
                    return

                try:
                    parser.parse()
                except ParserParsingError as error:
                    overfast_internal_error(parser.blizzard_url, error)
                    return

                parsers.append(parser)

        request_path = self.get_api_request_url(**kwargs)
        computed_data = self.merge_parsers_data(
            [parser.data for parser in parsers], **kwargs
        )

        # Generic route update
        self.cache_manager.update_api_cache(
            request_path, json.dumps(computed_data), self.timeout
        )

        logger.info("Updating route filters...")
        for route_filter in self.route_filters:
            filtered_path = f"{request_path}{route_filter['uri']}"
            parsers_data = [
                parser.filter_request_using_query(**route_filter["kwargs"])
                for parser in parsers
            ]
            filtered_data = self.merge_parsers_data(
                parsers_data, **route_filter["kwargs"]
            )
            dumped_filtered_data = json.dumps(filtered_data)
            self.cache_manager.update_api_cache(
                filtered_path, dumped_filtered_data, self.timeout
            )
        logger.info("Cache update done !")

    def get_api_request_url(self, **kwargs) -> str:
        """OverFast API Request URL for this Request Handler. It usually
        is a concatenation of API root url and query data (kwargs) if the
        RequestHandler supports it.
        """
        return self.api_root_url
