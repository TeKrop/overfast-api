"""Set of pydantic models describing errors returned by the API"""

from pydantic import BaseModel, Field


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
        examples=[
            (
                "An internal server error occurred during the process. The developer "
                "received a notification, but don't hesitate to create a GitHub "
                "issue if you want any news concerning the bug resolution : "
                "https://github.com/TeKrop/overfast-api/issues"
            ),
        ],
    )


class PlayerParserErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the player parser error",
        examples=["Player not found"],
    )


class HeroParserErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the hero parser error",
        examples=["Hero not found or not released yet"],
    )


class RateLimitErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the rate limit error and number of seconds before retrying",
        examples=[
            "API has been rate limited by Blizzard, please wait for 5 seconds before retrying"
        ],
    )
