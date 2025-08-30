"""List Heroes Controller module"""

from typing import ClassVar

from app.config import settings
from app.controllers import AbstractController

from ..parsers.hero_stats_summary_parser import HeroStatsSummaryParser


class GetHeroStatsSummaryController(AbstractController):
    """Get Hero Stats Summary Controller used in order to
    retrieve usage statistics for Overwatch heroes.
    """

    parser_classes: ClassVar[list[type]] = [HeroStatsSummaryParser]
    timeout = settings.heroes_path_cache_timeout
