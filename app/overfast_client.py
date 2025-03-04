import httpx
from fastapi import HTTPException, status

from .cache_manager import CacheManager
from .config import settings
from .helpers import send_discord_webhook_message
from .metaclasses import Singleton
from .overfast_logger import logger


class OverFastClient(metaclass=Singleton):
    def __init__(self):
        self.cache_manager = CacheManager()
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": (
                    f"OverFastAPI v{settings.app_version} - "
                    "https://github.com/TeKrop/overfast-api"
                ),
                "From": "valentin.porchet@proton.me",
            },
            http2=True,
            timeout=10,
            follow_redirects=True,
        )

    async def get(self, url: str) -> httpx.Response:
        """Make an HTTP GET request with custom headers and retrieve the result"""

        # First, check if we're being rate limited
        self._check_rate_limit()

        # Make the API call
        try:
            response = await self.client.get(url)
        except httpx.TimeoutException as error:
            # Sometimes Blizzard takes to much time to give a response (player profiles, etc.)
            raise self._blizzard_response_error(
                status_code=0,
                error="Blizzard took more than 10 seconds to respond, resulting in a timeout",
            ) from error
        except httpx.RemoteProtocolError as error:
            # Sometimes Blizzard sends an invalid response (search players, etc.)
            raise self._blizzard_response_error(
                status_code=0,
                error="Blizzard closed the connection, no data could be retrieved",
            ) from error

        logger.debug("OverFast request done !")

        # Make sure we catch HTTP 403 from Blizzard when it happens,
        # so we don't make any more call before some amount of time
        if response.status_code == status.HTTP_403_FORBIDDEN:
            raise self._blizzard_forbidden_error()

        return response

    async def aclose(self) -> None:
        """Properly close HTTPX Async Client"""
        await self.client.aclose()

    def _check_rate_limit(self) -> None:
        """Make sure we're not being rate limited by Blizzard before making
        any API call. Else, return an HTTP 429 with Retry-After header.
        """
        if self.cache_manager.is_being_rate_limited():
            raise self._too_many_requests_response(
                retry_after=self.cache_manager.get_global_rate_limit_remaining_time()
            )

    def blizzard_response_error_from_response(
        self, response: httpx.Response
    ) -> HTTPException:
        """Alias for sending Blizzard error from a request directly"""
        return self._blizzard_response_error(response.status_code, response.text)

    @staticmethod
    def _blizzard_response_error(status_code: int, error: str) -> HTTPException:
        """Retrieve a generic error response when a Blizzard page doesn't load"""
        logger.error(
            "Received an error from Blizzard. HTTP {} : {}",
            status_code,
            error,
        )

        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Couldn't get Blizzard page (HTTP {status_code} error) : {error}",
        )

    def _blizzard_forbidden_error(self) -> HTTPException:
        """Retrieve a generic error response when Blizzard returns forbidden error.
        Also prevent further calls to Blizzard for a given amount of time.
        """

        # We have to block future requests to Blizzard, cache the information on Redis
        self.cache_manager.set_global_rate_limit()

        # If Discord Webhook configuration is enabled, send a message to the
        # given channel using Discord Webhook URL
        send_discord_webhook_message(
            "Blizzard Rate Limit reached ! Blocking further calls for "
            f"{settings.blizzard_rate_limit_retry_after} seconds..."
        )

        return self._too_many_requests_response(
            retry_after=settings.blizzard_rate_limit_retry_after
        )

    @staticmethod
    def _too_many_requests_response(retry_after: int) -> HTTPException:
        """Generic method to return an HTTP 429 response with Retry-After header"""
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "API has been rate limited by Blizzard, please wait for "
                f"{retry_after} seconds before retrying"
            ),
            headers={settings.retry_after_header: str(retry_after)},
        )
