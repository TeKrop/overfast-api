"""Player profile page Parser module"""
from fastapi import status

from overfastapi.common.exceptions import ParserInitError
from overfastapi.parsers.api_parser import APIParser


class PlayerParser(APIParser):
    """Overwatch player profile page Parser class"""

    def __init__(self, html_content: str, **kwargs):
        super().__init__(html_content)
        self.player_id = kwargs.get("player_id")

        # We must check if we have expected section
        if not self.root_tag.find("section", id="overview-section"):
            raise ParserInitError(
                status_code=status.HTTP_404_NOT_FOUND, message="Player not found"
            )

    def parse_data(self) -> dict:
        return {}
