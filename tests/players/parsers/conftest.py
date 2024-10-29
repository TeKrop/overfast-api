import pytest
from _pytest.fixtures import SubRequest

from app.players.parsers.player_career_parser import PlayerCareerParser
from app.players.parsers.player_parser import PlayerParser
from app.players.parsers.player_stats_summary_parser import PlayerStatsSummaryParser
from app.players.parsers.search_data_parser import NamecardParser


@pytest.fixture(scope="package")
def namecard_parser(request: SubRequest) -> NamecardParser:
    return NamecardParser(player_id=request.param)


@pytest.fixture(scope="package")
def player_parser(request: SubRequest) -> PlayerParser:
    return PlayerParser(player_id=request.param)


@pytest.fixture(scope="package")
def player_stats_summary_parser(request: SubRequest) -> PlayerStatsSummaryParser:
    return PlayerStatsSummaryParser(player_id=request.param)


@pytest.fixture(scope="package")
def player_career_parser(request: SubRequest) -> PlayerCareerParser:
    return PlayerCareerParser(player_id=request.param)
