from itertools import batched
from typing import ClassVar

import httpx

from app.cache_manager import CacheManager
from app.config import settings
from app.enums import Locale
from app.helpers import send_discord_webhook_message
from app.overfast_logger import logger
from app.players.enums import UnlockDataType

from .metaclasses import Singleton


class UnlocksManager(metaclass=Singleton):
    """Unlock manager main class, containing methods to retrieve
    and store data for unlocks : avatars, namecards, titles.
    """

    # Mapping between Blizzard type and API type
    data_type_mapping: ClassVar[dict[str, UnlockDataType]] = {
        "Player Icons": UnlockDataType.PORTRAIT,
        "Name Cards": UnlockDataType.NAMECARD,
        "Player Titles": UnlockDataType.TITLE,
    }

    # Mapping between API type and value key in Blizzard data
    data_value_mapping: ClassVar[dict[UnlockDataType, str]] = {
        UnlockDataType.PORTRAIT: "icon",
        UnlockDataType.NAMECARD: "icon",
        UnlockDataType.TITLE: "name",
    }

    def __init__(self):
        self.cache_manager = CacheManager()

    def get(self, unlock_id: str) -> str | None:
        """Retrieve unlock value from cache"""
        return self.cache_manager.get_unlock_data_cache(unlock_id)

    def cache_values(self, unlock_ids: set[str]) -> None:
        """Cache values for unlock ids"""

        # We'll ignore already cached unlock values
        missing_unlock_ids = {
            unlock_id for unlock_id in unlock_ids if not self.get(unlock_id)
        }

        # If everything is already cached, no need to do anything
        if not missing_unlock_ids:
            return

        logger.info("Retrieving {} missing unlock ids...", len(missing_unlock_ids))

        # Make an API call to Blizzard to retrieve and cache values
        try:
            raw_unlock_data = self._get_unlock_data_from_blizzard(missing_unlock_ids)
        except httpx.RequestError as err:
            error_message = f"Error while retrieving unlock data from Blizzard : {err}"
            logger.exception(error_message)
            send_discord_webhook_message(error_message)
            return

        # Loop over the results and store data value depending on unlock type
        unlock_data: dict[str, str] = {
            data["id"]: data[self.data_value_mapping[unlock_type]]
            for data in raw_unlock_data
            if (unlock_type := self.data_type_mapping.get(data["type"]["name"]))
        }

        self.cache_manager.update_unlock_data_cache(unlock_data)

    def _get_unlock_data_from_blizzard(self, unlock_ids: set[str]) -> list[dict]:
        """Retrieve unlock data from Blizzard. Chunk API calls as there is a limit."""
        unlock_data: list[dict] = []

        for batch in batched(unlock_ids, settings.unlock_data_batch_size, strict=False):
            try:
                response = httpx.get(
                    f"{settings.blizzard_host}/{Locale.ENGLISH_US}{settings.unlock_data_path}",
                    params={"unlockIds": ",".join(batch)},
                )
            except httpx.RequestError as err:
                error_message = (
                    f"Error while retrieving unlock data from Blizzard : {err}"
                )
                logger.error(error_message)
                send_discord_webhook_message(error_message)
                return None

            unlock_data.extend(response.json())

        return unlock_data
