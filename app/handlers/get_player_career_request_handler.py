"""Player Career Request Handler module"""

from typing import ClassVar

from app.common.enums import SearchDataType
from app.config import settings
from app.parsers.player_parser import PlayerParser
from app.parsers.search_data_parser import LastUpdatedAtParser, NamecardParser

from .api_request_handler import APIRequestHandler


class GetPlayerCareerRequestHandler(APIRequestHandler):
    """Player Career Request Handler used in order to retrieve data about a player
    Overwatch career : summary, statistics about heroes, etc. using the
    PlayerParser class.
    """

    parser_classes: ClassVar[list] = [PlayerParser, NamecardParser, LastUpdatedAtParser]
    timeout = settings.career_path_cache_timeout

    def merge_parsers_data(self, parsers_data: list[dict], **kwargs) -> dict:
        """Merge parsers data together : PlayerParser for statistics data,
        NamecardParser for namecard and LastUpdatedAtParser
        for last time the player profile was updated
        """

        # If the user asked for stats, no need to add the namecard
        if kwargs.get("stats"):
            return parsers_data[0]

        # Retrieve the summary depending on kwargs
        summary = (
            parsers_data[0] if kwargs.get("summary") else parsers_data[0]["summary"]
        )
        namecard_value = parsers_data[1][SearchDataType.NAMECARD]
        last_updated_at_value = parsers_data[2][SearchDataType.LAST_UPDATED_AT]

        # We want to insert the namecard before "title" key in "summary"
        title_pos = list(summary.keys()).index("title")
        summary_items = list(summary.items())
        summary_items.insert(title_pos, ("namecard", namecard_value))
        summary = dict(summary_items)

        # We can insert the last_updated_at at the end
        summary["last_updated_at"] = last_updated_at_value

        if kwargs.get("summary"):
            return summary

        parsers_data[0]["summary"] = summary
        return parsers_data[0]
