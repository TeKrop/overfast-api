"""Search Data Parser module"""

from typing import ClassVar

from app.config import settings
from app.parsers import JSONParser
from app.players.enums import PlayerGamemode, PlayerPlatform, PlayerRegion


class HeroStatsSummaryParser(JSONParser):
    """Static Data Parser class"""

    request_headers_headers: ClassVar[dict] = JSONParser.request_headers | {
        "X-Requested-With": "XMLHttpRequest"
    }

    root_path: str = settings.hero_stats_path

    platform_mapping: ClassVar[dict[PlayerPlatform, str]] = {
        PlayerPlatform.PC: "PC",
        PlayerPlatform.CONSOLE: "Console",
    }

    gamemode_mapping: ClassVar[dict[PlayerGamemode, str]] = {
        PlayerGamemode.QUICKPLAY: "0",
        PlayerGamemode.COMPETITIVE: "1",
    }

    region_mapping: ClassVar[dict[PlayerRegion, str]] = {
        PlayerRegion.EUROPE: "Europe",
        PlayerRegion.AMERICAS: "Americas",
        PlayerRegion.ASIA: "Asia",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.order_by: str | None = kwargs.get("order_by")
        self.role_filter: str | None = kwargs.get("role")

    async def parse_data(self) -> dict:
        return [
            {
                "key": rate["id"],
                "name": rate["hero"]["name"],
                "pickrate": rate["cells"]["pickrate"],
                "winrate": rate["cells"]["winrate"],
            }
            for rate in self.json_data["rates"]
            if (
                self.role_filter is None
                or rate["hero"]["role"].lower() == self.role_filter
            )
        ]

    def get_blizzard_query_params(self, **kwargs) -> dict:
        platform_filter = self.platform_mapping[kwargs["platform"]]
        gamemode_filter = self.gamemode_mapping[kwargs["gamemode"]]
        region_filter = self.region_mapping[kwargs["region"]]

        # tier
        # map

        return {
            "input": platform_filter,
            "rq": gamemode_filter,
            "region": region_filter,
        }
