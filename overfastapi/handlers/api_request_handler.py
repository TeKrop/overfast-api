"""Abstract API Request Handler module"""
import json
from abc import ABC, abstractmethod
from functools import cached_property

from fastapi import HTTPException, Request

from overfastapi.common.cache_manager import CacheManager
from overfastapi.common.exceptions import ParserInitError, ParserParsingError
from overfastapi.common.helpers import (
    blizzard_response_error,
    overfast_internal_error,
    overfast_request,
)
from overfastapi.common.logging import logger
from overfastapi.common.mixins import ApiRequestMixin
from overfastapi.config import BLIZZARD_HOST
from overfastapi.parsers.api_parser import APIParser


class APIRequestHandler(ApiRequestMixin, ABC):
    """Generic abstract API Request Handler, containing attributes structure and methods
    in order to quickly be able to create concrete request handlers. The blizzard URL
    call, and the API Cache / Parser Cache systems are handled here.
    """

    route_filters = []
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
    def root_path(self) -> str:
        """Root path of the Blizzard URL containing the data (/en-us/career/, etc."""

    @property
    @abstractmethod
    def parser_class(self) -> type:
        """Parser class used for parsing the Blizzard page retrieved with this handler"""

    @property
    @abstractmethod
    def timeout(self) -> int:
        """Timeout used for API Cache storage for this specific handler"""

    def process_request(self, **kwargs) -> dict:
        """Main method used to process the request from user and return final data. Raises
        an HTTPException in case of error when retrieving or parsing data.

        The process uses API/Parser Cache if available and needed, the main steps are :
        - Make a request to Blizzard URL (if not using Cache API)
        - Instanciate the dedicated parser class with Blizzard response
        - Return Parser Cache if available, and update API Cache accordingly
        - Else, parse the page completely, and update all related caches in background
        - Then, filter the data using kwargs parameters, and return the final data
        """

        # If we are using API Cache from inside the app
        # (no reverse proxy configured), check the API Cache
        if api_cache_data := self.get_api_cache_data():
            return api_cache_data

        # No API Cache or not using it in app, we request the data from Blizzard page
        logger.info("No API Cache, requesting the data to Blizzard...")
        blizzard_url = self.get_blizzard_url(**kwargs)
        req = overfast_request(blizzard_url)
        if req.status_code != 200:
            raise blizzard_response_error(req)

        # Check the Parser cache with received page calculated hash
        logger.info("Done ! Instanciating dedicated Parser...")
        try:
            parser = self.parser_class(req.text, **kwargs)
        except ParserInitError as error:
            logger.error("Failed to instanciate Parser : {}", error.message)
            raise HTTPException(
                status_code=error.status_code, detail=error.message
            ) from error

        logger.info("Done ! Checking Parser Cache...")
        parser_cache_data = self.cache_manager.get_unchanged_parser_cache(
            self.cache_key, parser.hash
        )
        if parser_cache_data:
            logger.info("Parser Cache found ! ")
            # Parser cache is already valid, just update the API cache
            self.cache_manager.update_api_cache(
                self.cache_key, parser_cache_data, self.timeout
            )
            return json.loads(parser_cache_data)

        # No cache is valid, we need to parse the data and update the cache
        logger.info("No valid Parser Cache found, parsing the page...")

        try:
            parser.parse()
        except ParserParsingError as error:
            raise overfast_internal_error(blizzard_url, error) from error

        # Do all the cache update in background
        logger.info("Updating all related caches in background...")
        kwargs["background_tasks"].add_task(
            self.update_all_cache,
            parser,
            **kwargs,
        )

        # Return the filtered data
        logger.info("Filtering the data using query...")
        filtered_data = self.filter_request_using_query(parser.data, **kwargs)

        logger.info("Done ! Returning filtered data...")
        return filtered_data

    def update_all_cache(self, parser: APIParser = None, **kwargs) -> None:
        """Update all cache values (API and Parser) concerning the given parser (if any)
        and the given kwargs (GET parameters on API request in general).

        The main steps of the process are :
        - If no parser was given, instanciate one using kwargs and parse the data
        - Update root path caches (API and Parser)
        - Update subroutes caches (API and Parser). For example, for the player career
        route, it will update the cache for the summary route, stats, achivements, etc.
        """
        logger.info("Starting to update all caches...")

        if parser is None:
            logger.info("No parser was given for updating cache, instanciating one...")
            req = overfast_request(self.get_blizzard_url(**kwargs))
            if req.status_code != 200:
                logger.error(
                    "Received an error from Blizzard. HTTP {} : {}",
                    req.status_code,
                    req.text,
                )
                return
            parser = self.parser_class(req.text, **kwargs)
            parser.parse()
            logger.info("Parser instanciated !")

        request_path = self.get_api_request_url(**kwargs)

        dumped_parsed_data = json.dumps(parser.data)

        # Update root path Parser Cache and API Cache
        logger.info("Updating Parser and API Cache...")
        self.cache_manager.update_parser_cache(
            request_path, {"hash": parser.hash, "data": dumped_parsed_data}
        )
        self.cache_manager.update_api_cache(
            request_path, dumped_parsed_data, self.timeout
        )

        # Update all subroutes Parser Cache and API Cache
        logger.info("Updating route filters...")
        for route_filter in self.route_filters:
            filtered_path = f"{request_path}{route_filter['uri']}"
            filtered_data = self.filter_request_using_query(
                parser.data, **route_filter["kwargs"]
            )
            dumped_filtered_data = json.dumps(filtered_data)
            self.cache_manager.update_parser_cache(
                filtered_path, {"hash": parser.hash, "data": dumped_filtered_data}
            )
            self.cache_manager.update_api_cache(
                filtered_path, dumped_filtered_data, self.timeout
            )
        logger.info("Cache update done !")

    @staticmethod
    def filter_request_using_query(
        parsed_data: dict | list, **kwargs  # pylint: disable=W0613
    ) -> dict | list:
        """If the route contains subroutes accessible using GET queries, this method
        will filter Blizzard data using the query data. This method should be
        redefined in child classes if needed. The default behaviour is to return
        the parsed data directly.
        """
        return parsed_data

    @cached_property
    def blizzard_root_url(self) -> str:
        """Property containing Root URL for requesting data to Blizzard"""
        return f"{BLIZZARD_HOST}{self.root_path}"

    def get_blizzard_url(self, **kwargs) -> str:  # pylint: disable=W0613
        """URL used when requesting data to Blizzard. It usually is a concatenation
        of root url and query data (kwargs) if the RequestHandler supports it.
        For example : single hero page (hero key), player career page (platform and
        player id, etc.). Default is just the blizzard root url.
        """
        return self.blizzard_root_url

    def get_api_request_url(self, **kwargs) -> str:  # pylint: disable=W0613
        """OverFast API Request URL for this Request Handler. It usually
        is a concatenation of API root url and query data (kwargs) if the
        RequestHandler supports it.
        """
        return self.api_root_url
