"""Abstract API Controller module"""

import json
from abc import ABC, abstractmethod

from fastapi import HTTPException, Request, Response

from .adapters.storage import SQLiteStorage
from .cache_manager import CacheManager
from .config import settings
from .exceptions import ParserBlizzardError, ParserParsingError
from .helpers import get_human_readable_duration, overfast_internal_error
from .monitoring.metrics import storage_write_errors_total
from .overfast_logger import logger


class AbstractController(ABC):
    """Generic Abstract API Controller, containing attributes structure and methods
    in order to quickly be able to create concrete controllers. A controller can
    be associated with several parsers (one parser = one Blizzard page parsing).
    The API Cache system is handled here.
    """

    # Generic cache manager class, used to manipulate Valkey cache data
    cache_manager = CacheManager()

    # Storage adapter for persistent data
    storage = SQLiteStorage()

    def __init__(self, request: Request, response: Response):
        self.cache_key = CacheManager.get_cache_key_from_request(request)
        self.response = response

    @property
    @classmethod
    @abstractmethod
    def parser_classes(cls) -> list[type]:
        """Parser classes used for parsing the Blizzard page retrieved with this controller"""

    @property
    @classmethod
    @abstractmethod
    def timeout(cls) -> int:
        """Timeout used for API Cache storage for this specific controller"""

    @classmethod
    def get_human_readable_timeout(cls) -> str:
        return get_human_readable_duration(cls.timeout)

    async def update_static_cache(
        self, data: dict | list, storage_key: str, data_type: str = "json"
    ) -> None:
        """
        Dual-write static data to both Valkey cache and SQLite storage.

        Args:
            data: Data to cache (will be JSON-serialized)
            storage_key: Key for SQLite storage (e.g., "heroes:en-us")
            data_type: Type of data ("json" or "html")
        """
        # Update API Cache (Valkey) - async
        await self.cache_manager.update_api_cache(self.cache_key, data, self.timeout)

        # Update persistent storage (SQLite) - Phase 3 dual-write
        try:
            json_data = json.dumps(data, separators=(",", ":"))
            await self.storage.put_static(
                key=storage_key, data=json_data, data_type=data_type
            )
        except OSError as error:
            # Disk/file I/O errors
            logger.warning(
                f"Storage write failed (disk error) for {storage_key}: {error}"
            )
            self._track_storage_error("disk_error")
        except RuntimeError as error:
            # Compression/serialization errors
            logger.warning(
                f"Storage write failed (compression error) for {storage_key}: {error}"
            )
            self._track_storage_error("compression_error")
        except Exception as error:  # noqa: BLE001
            # Unexpected errors
            logger.error(f"Storage write failed (unknown) for {storage_key}: {error}")
            self._track_storage_error("unknown")

    @staticmethod
    def _track_storage_error(error_type: str) -> None:
        """Track storage write errors in Prometheus if enabled"""
        if settings.prometheus_enabled:
            storage_write_errors_total.labels(error_type=error_type).inc()

    async def process_request(self, **kwargs) -> dict | list:
        """Main method used to process the request from user and return final data. Raises
        an HTTPException in case of error when retrieving or parsing data.

        The main steps are :
        - Instanciate the dedicated parser classes in order to retrieve Blizzard data
            - Depending on the parser, an intermediary cache can be used in the process
        - Filter the data using kwargs parameters, then merge the data from parsers
        - Update related API Cache and return the final data
        """

        # Instance parsers and request data
        parsers_data = []
        for parser_class in self.parser_classes:
            parser = parser_class(**kwargs)

            try:
                await parser.parse()
            except ParserBlizzardError as error:
                raise HTTPException(
                    status_code=error.status_code,
                    detail=error.message,
                ) from error
            except ParserParsingError as error:
                raise overfast_internal_error(parser.blizzard_url, error) from error

            # Filter the data to obtain final parser data
            logger.info("Filtering the data using query...")
            parsers_data.append(parser.filter_request_using_query(**kwargs))

        # Merge parsers data together
        computed_data = self.merge_parsers_data(parsers_data, **kwargs)

        # Update API Cache - async
        await self.cache_manager.update_api_cache(
            self.cache_key, computed_data, self.timeout
        )

        # Ensure response headers contains Cache TTL
        self.response.headers[settings.cache_ttl_header] = str(self.timeout)

        logger.info("Done ! Returning filtered data...")
        return computed_data

    def merge_parsers_data(self, parsers_data: list[dict | list], **_) -> dict | list:
        """Merge parsers data together. It depends on the given route and datas,
        and needs to be overriden in case a given Controller is associated
        with several Parsers.
        """
        return parsers_data[0]
