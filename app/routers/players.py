"""Players endpoints router : players search, players career, statistics, etc."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, status

from app.common.decorators import validation_error_handler
from app.common.enums import (
    HeroKeyCareerFilter,
    PlayerGamemode,
    PlayerPlatform,
    RouteTag,
)
from app.common.helpers import routes_responses as common_routes_responses
from app.handlers.get_player_career_request_handler import GetPlayerCareerRequestHandler
from app.handlers.get_player_career_stats_request_handler import (
    GetPlayerCareerStatsRequestHandler,
)
from app.handlers.get_player_stats_summary_request_handler import (
    GetPlayerStatsSummaryRequestHandler,
)
from app.handlers.search_players_request_handler import SearchPlayersRequestHandler
from app.models.errors import PlayerParserErrorMessage
from app.models.players import (
    CareerStats,
    Player,
    PlayerCareerStats,
    PlayerSearchResult,
    PlayerStatsSummary,
    PlayerSummary,
)

# Custom route responses for player careers
career_routes_responses = {
    status.HTTP_404_NOT_FOUND: {
        "model": PlayerParserErrorMessage,
        "description": "Player Not Found",
    },
    **common_routes_responses,
}


async def get_player_common_parameters(
    player_id: str = Path(
        title="Player unique name",
        description=(
            'Identifier of the player : BattleTag (with "#" replaced by "-"). '
            "Be careful, letter case (capital/non-capital letters) is important !"
        ),
        examples=["TeKrop-2217"],
    ),
):
    return {"player_id": player_id}


CommonsPlayerDep = Annotated[dict, Depends(get_player_common_parameters)]


async def get_player_career_common_parameters(
    commons: CommonsPlayerDep,
    gamemode: PlayerGamemode = Query(
        ...,
        title="Gamemode",
        description="Filter on a specific gamemode.",
        examples=["competitive"],
    ),
    platform: PlayerPlatform = Query(
        None,
        title="Platform",
        description=(
            "Filter on a specific platform. If not specified, the only platform the "
            "player played on will be selected. If the player has already played on "
            "both PC and console, the PC stats will be displayed by default."
        ),
        examples=["pc"],
    ),
    hero: HeroKeyCareerFilter = Query(
        None,
        title="Hero key",
        description=(
            "Filter on a specific hero in order to only get his statistics. "
            "You also can specify 'all-heroes' for general stats."
        ),
    ),
):
    return {
        "player_id": commons.get("player_id"),
        "gamemode": gamemode,
        "platform": platform,
        "hero": hero,
    }


CommonsPlayerCareerDep = Annotated[dict, Depends(get_player_career_common_parameters)]

router = APIRouter()


@router.get(
    "",
    responses=common_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Search for a specific player",
    description=(
        "Search for a given player by using his username. You should be able to "
        "find the associated player_id to use in order to request career data."
        "<br />**Cache TTL : 1 hour.**"
    ),
    operation_id="search_players",
)
@validation_error_handler(response_model=PlayerSearchResult)
async def search_players(
    request: Request,
    name: str = Query(
        title="Player nickname to search",
        examples=["TeKrop"],
    ),
    order_by: str = Query(
        "name:asc",
        title="Ordering field and the way it's arranged (asc[ending]/desc[ending])",
        pattern=r"^(player_id|name|last_updated_at):(asc|desc)$",
    ),
    offset: int = Query(0, title="Offset of the results", ge=0),
    limit: int = Query(20, title="Limit of results per page", gt=0),
) -> PlayerSearchResult:
    return await SearchPlayersRequestHandler(request).process_request(
        name=name,
        order_by=order_by,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{player_id}/summary",
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get player summary",
    description=(
        "Get player summary : name, avatar, competitive ranks, etc. "
        "<br />**Cache TTL : 1 hour.**"
    ),
    operation_id="get_player_summary",
)
@validation_error_handler(response_model=PlayerSummary)
async def get_player_summary(
    request: Request,
    commons: CommonsPlayerDep,
) -> PlayerSummary:
    return await GetPlayerCareerRequestHandler(request).process_request(
        summary=True,
        player_id=commons.get("player_id"),
    )


@router.get(
    "/{player_id}/stats/summary",
    response_model_exclude_unset=True,
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get player stats summary",
    description=(
        "Get player statistics summary, with stats usually used for tracking "
        "progress : winrate, kda, damage, healing, etc. "
        "<br /> Data is regrouped in 3 sections : general (sum of all stats), "
        "roles (sum of stats for each role) and heroes (stats for each hero)."
        "<br /> Depending on filters, data from both competitive and quickplay, "
        "and/or pc and console will be merged."
        "<br />Default behaviour : all gamemodes and platforms are taken in account."
        "<br />**Cache TTL : 1 hour.**"
    ),
    operation_id="get_player_stats_summary",
)
@validation_error_handler(response_model=PlayerStatsSummary)
async def get_player_stats_summary(
    request: Request,
    commons: CommonsPlayerDep,
    gamemode: PlayerGamemode = Query(
        None,
        title="Gamemode",
        description=(
            "Filter on a specific gamemode. If not specified, the data of "
            "every gamemode will be combined."
        ),
        examples=["competitive"],
    ),
    platform: PlayerPlatform = Query(
        None,
        title="Platform",
        description=(
            "Filter on a specific platform. If not specified, the data of "
            "every platform will be combined."
        ),
        examples=["pc"],
    ),
) -> PlayerStatsSummary:
    return await GetPlayerStatsSummaryRequestHandler(request).process_request(
        player_id=commons.get("player_id"),
        platform=platform,
        gamemode=gamemode,
    )


@router.get(
    "/{player_id}/stats/career",
    response_model_exclude_unset=True,
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get player career stats",
    description=(
        "Career contains numerous statistics grouped by heroes and categories "
        "(combat, game, best, hero specific, average, etc.). Filter them on "
        "specific platform and gamemode (mandatory). You can even retrieve "
        "data about a specific hero of your choice."
        "<br />**Cache TTL : 1 hour.**"
    ),
    operation_id="get_player_career_stats",
)
@validation_error_handler(response_model=PlayerCareerStats)
async def get_player_career_stats(
    request: Request,
    commons: CommonsPlayerCareerDep,
) -> PlayerCareerStats:
    return await GetPlayerCareerStatsRequestHandler(request).process_request(
        stats=True,
        **commons,
    )


@router.get(
    "/{player_id}/stats",
    response_model_exclude_unset=True,
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get player stats with labels",
    description=(
        "This endpoint exposes the same data as the previous one, except it also "
        "exposes labels of the categories and statistics."
        "<br />**Cache TTL : 1 hour.**"
    ),
    operation_id="get_player_stats",
)
@validation_error_handler(response_model=CareerStats)
async def get_player_stats(
    request: Request,
    commons: CommonsPlayerCareerDep,
) -> CareerStats:
    return await GetPlayerCareerRequestHandler(request).process_request(
        stats=True,
        **commons,
    )


@router.get(
    "/{player_id}",
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get all player data",
    description=(
        "Get all player data : summary and statistics with labels.<br />**Cache TTL : 1 hour.**"
    ),
    operation_id="get_player_career",
)
@validation_error_handler(response_model=Player)
async def get_player_career(
    request: Request,
    commons: CommonsPlayerDep,
) -> Player:
    return await GetPlayerCareerRequestHandler(request).process_request(
        player_id=commons.get("player_id"),
    )
