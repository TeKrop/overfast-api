"""Set of mixins for the project"""
import json

from app.config import settings

from .logging import logger


class ApiRequestMixin:
    """Mixin used in API Request handler classes"""

    def get_api_cache_data(self) -> dict | list | None:
        """Retrieve API cache data if any and if it's configured to be retrieved in-app"""
        logger.info("Checking API Cache (if enabled)...")

        if not settings.use_api_cache_in_app:
            return None

        api_cache_data = self.cache_manager.get_api_cache(self.cache_key)
        if not api_cache_data:
            return None

        logger.info("API Cache found ! Returning it")
        return json.loads(api_cache_data)
