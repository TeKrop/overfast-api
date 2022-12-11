"""Players endpoints router : players search, players career, statistics, etc."""
from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Request, status

from overfastapi.common.decorators import validation_error_handler
from overfastapi.common.enums import (
    HeroKeyCareerFilter,
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
    player_id: str = Path(
        title="Player unique name",
        description=(
            'Identifier of the player : BattleTag (with "#" replaced by "-"). '
            "Be careful, letter case (capital/non-capital letters) is important !"
        ),
        example="TeKrop-2217",
    ),
):
    return {"player_id": player_id}


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
    background_tasks: BackgroundTasks,
    request: Request,
    name: str = Query(
        title="Player nickname to search",
        example="TeKrop",
    ),
    privacy: PlayerPrivacy
    | None = Query(
        None, title="Privacy settings of the player career", example="public"
    ),
    order_by: str
    | None = Query(
        "name:asc",
        title="Ordering field and the way it's arranged (asc[ending]/desc[ending])",
        regex="^(player_id|name|privacy):(asc|desc)$",
    ),
    offset: int | None = Query(0, title="Offset of the results", ge=0),
    limit: int | None = Query(20, title="Limit of results per page", gt=0),
):
    return SearchPlayersRequestHandler(request).process_request(
        name=name,
        privacy=privacy,
        order_by=order_by,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{player_id}",
    response_model=Player,
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get player career data",
    description="Get all player data : summary and statistics",
)
@validation_error_handler(response_model=Player)
async def get_player_career(
    background_tasks: BackgroundTasks,
    request: Request,
    commons: dict = Depends(get_player_common_parameters),
):
    return GetPlayerCareerRequestHandler(request).process_request(
        background_tasks=background_tasks,
        player_id=commons.get("player_id"),
    )


@router.get(
    "/{player_id}/summary",
    response_model=PlayerSummary,
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get player summary",
    description="Get player summary : name, avatar, competitive ranks, etc.",
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
        player_id=commons.get("player_id"),
    )


@router.get(
    "/{player_id}/stats",
    response_model=CareerStats,
    response_model_exclude_unset=True,
    responses=career_routes_responses,
    tags=[RouteTag.PLAYERS],
    summary="Get player statistics",
    description=(
        "Career contains numerous statistics grouped by heroes and categories "
        "(combat, game, best, hero specific, average, etc.). Filter them on "
        "specific platform and gamemode (mandatory). You can even retrieve "
        "data about a specific hero of your choice."
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
        example="competitive",
    ),
    platform: PlayerPlatform
    | None = Query(
        None,
        title="Platform",
        description=(
            "Filter on a specific platform. If not specified, the only platform the "
            "player played on will be selected. If the player has already played on "
            "both PC and console, the PC stats will be displayed by default."
        ),
        example="pc",
    ),
    hero: HeroKeyCareerFilter
    | None = Query(
        None,
        title="Hero key",
        description=(
            "Filter on a specific hero in order to only get his statistics. "
            "You also can specify 'all-heroes' for general stats."
        ),
    ),
):
    return GetPlayerCareerRequestHandler(request).process_request(
        stats=True,
        background_tasks=background_tasks,
        player_id=commons.get("player_id"),
        platform=platform,
        gamemode=gamemode,
        hero=hero,
    )
