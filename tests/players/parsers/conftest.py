from typing import TYPE_CHECKING

import pytest

from app.players.parsers.player_career_parser import PlayerCareerParser
from app.players.parsers.player_career_stats_parser import PlayerCareerStatsParser
from app.players.parsers.player_stats_summary_parser import PlayerStatsSummaryParser

if TYPE_CHECKING:
    from _pytest.fixtures import SubRequest


@pytest.fixture(scope="package")
def player_career_parser(request: SubRequest) -> PlayerCareerParser:
    return PlayerCareerParser(player_id=request.param)


@pytest.fixture(scope="package")
def player_stats_summary_parser(request: SubRequest) -> PlayerStatsSummaryParser:
    return PlayerStatsSummaryParser(player_id=request.param)


@pytest.fixture(scope="package")
def player_career_stats_parser(request: SubRequest) -> PlayerCareerStatsParser:
    return PlayerCareerStatsParser(player_id=request.param)
