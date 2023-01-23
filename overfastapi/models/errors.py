"""Set of pydantic models describing errors returned by the API"""
from pydantic import BaseModel, Field


class BlizzardErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the error",
        example="Couldn't get Blizzard page (HTTP 503 error) : Service Unavailable",
    )


class InternalServerErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the internal server error",
        example=(
            "An internal server error occurred during the process. The developer "
            "received a notification, but don't hesitate to create a GitHub "
            "issue if you want any news concerning the bug resolution : "
            "https://github.com/TeKrop/overfast-api/issues"
        ),
    )


class ParserErrorMessage(BaseModel):
    error: str = Field(
        ...,
        description="Message describing the error",
        example="Player not found",
    )
