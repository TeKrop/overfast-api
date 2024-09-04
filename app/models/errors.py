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
