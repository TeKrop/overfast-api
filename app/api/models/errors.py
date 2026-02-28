"""Set of pydantic models describing errors returned by the API"""

from pydantic import BaseModel, Field

from app.config import settings


class BlizzardErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the error",
        examples=["Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable"],
    )


class InternalServerErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the internal server error",
        examples=[settings.internal_server_error_message],
    )


class RateLimitErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the rate limit error and number of seconds before retrying",
        examples=[
            "API has been rate limited by Blizzard, please wait for 5 seconds before retrying"
        ],
    )
