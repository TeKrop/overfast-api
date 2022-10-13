# pylint: disable=R0913,C0116
"""Players endpoints router : players search, players career, statistics, etc."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Request, status

from overfastapi.common.decorators import validation_error_handler
from overfastapi.common.enums import (
    HeroKey,
    PlayerAchievementCategory,
    PlayerGamemode,
    PlayerPlatform,
    PlayerPrivacy,
    RouteTag,
)
from overfastapi.common.helpers import routes_responses as common_routes_responses
from overfastapi.handlers.get_player_career_request_handler import (
    GetPlayerCareerRequestHandler,
)
from overfastapi.handlers.search_players_request_handler import (
    SearchPlayersRequestHandler,
)
from overfastapi.models.errors import ParserInitErrorMessage
from overfastapi.models.players import (
    CareerStats,
    Player,
    PlayerAchievementsContainer,
    PlayerSearchResult,
    PlayerSummary,
)

# Custom route responses for player careers
career_routes_responses = {
    status.HTTP_404_NOT_FOUND: {
        "model": ParserInitErrorMessage,
        "description": "Player Not Found",
    },
    **common_routes_responses,
}


async def get_player_common_parameters(
    platform: PlayerPlatform = Path(
        title="Platform on which the player is", example="pc"
    ),
    player_id: str = Path(
        title="Player unique name",
        description=(
            'Identifier of the player : BattleTag (with "#" replaced by "-") for '
            "PC players, nickname for PSN/XBL players, nickname followed by "
            "hexadecimal id for Nintendo Switch."
        ),
        example="TeKrop-2217",
    ),
):
    return {"platform": platform, "player_id": player_id}


router = APIRouter()


@router.get(
    "",
    response_model=PlayerSearchResult,
    responses=common_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Search for a specific player",
)
@validation_error_handler(response_model=PlayerSearchResult)
async def search_players(
    request: Request,
    name: str = Query(
        title="Player nickname to search",
        example="TeKrop",
    ),
    platform: Optional[PlayerPlatform] = Query(
        None, title="Platform on which the player is", example="pc"
    ),
    privacy: Optional[PlayerPrivacy] = Query(
        None, title="Privacy settings of the player career", example="public"
    ),
    order_by: Optional[str] = Query(
        "name:asc",
        title="Ordering field and the way it's arranged (asc[ending]/desc[ending])",
        regex="^(player_id|name|platform|privacy):(asc|desc)$",
    ),
    offset: Optional[int] = Query(0, title="Offset of the results", ge=0),
    limit: Optional[int] = Query(20, title="Limit of results per page", gt=0),
):
    return SearchPlayersRequestHandler(request).process_request(
        name=name,
        privacy=privacy,
        platform=platform,
        order_by=order_by,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{platform}/{player_id}",
    response_model=Player,
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get player career data",
    description="Get all player data : summary, statistics and achievements",
)
@validation_error_handler(response_model=Player)
async def get_player_career(
    background_tasks: BackgroundTasks,
    request: Request,
    commons: dict = Depends(get_player_common_parameters),
):
    return GetPlayerCareerRequestHandler(request).process_request(
        background_tasks=background_tasks,
        platform=commons.get("platform"),
        player_id=commons.get("player_id"),
    )


@router.get(
    "/{platform}/{player_id}/summary",
    response_model=PlayerSummary,
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get player summary",
)
@validation_error_handler(response_model=PlayerSummary)
async def get_player_summary(
    background_tasks: BackgroundTasks,
    request: Request,
    commons: dict = Depends(get_player_common_parameters),
):
    return GetPlayerCareerRequestHandler(request).process_request(
        summary=True,
        background_tasks=background_tasks,
        platform=commons.get("platform"),
        player_id=commons.get("player_id"),
    )


@router.get(
    "/{platform}/{player_id}/stats",
    response_model=CareerStats,
    response_model_exclude_unset=True,
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get player statistics about heroes",
    description=(
        "Career contains numerous statistics "
        "grouped by heroes and categories (combat, game, best, hero specific, "
        "average, etc.), while heroes comparisons contains generic details grouped "
        "by main categories (time played, games won, objective kills, etc.)"
    ),
)
@validation_error_handler(response_model=CareerStats)
async def get_player_stats(
    background_tasks: BackgroundTasks,
    request: Request,
    commons: dict = Depends(get_player_common_parameters),
    gamemode: PlayerGamemode = Query(
        ...,
        title="Gamemode",
        description="Filter on a specific gamemode.",
    ),
    hero: Optional[HeroKey] = Query(
        None,
        title="Hero key",
        description="Filter on a specific hero in order to only get his statistics.",
    ),
):
    return GetPlayerCareerRequestHandler(request).process_request(
        stats=True,
        background_tasks=background_tasks,
        platform=commons.get("platform"),
        player_id=commons.get("player_id"),
        gamemode=gamemode,
        hero=hero,
    )


@router.get(
    "/{platform}/{player_id}/achievements",
    response_model=PlayerAchievementsContainer,
    response_model_exclude_unset=True,
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get player achievements",
)
@validation_error_handler(response_model=PlayerAchievementsContainer)
async def get_player_achievements(
    background_tasks: BackgroundTasks,
    request: Request,
    commons: dict = Depends(get_player_common_parameters),
    category: Optional[PlayerAchievementCategory] = Query(
        None,
        title="Achievements category",
        description="Filter on specific achievements category",
    ),
):
    return GetPlayerCareerRequestHandler(request).process_request(
        achievements=True,
        background_tasks=background_tasks,
        platform=commons.get("platform"),
        player_id=commons.get("player_id"),
        category=category,
    )
