"""FastAPI routers for all API endpoints"""

from .routers.gamemodes import router as gamemodes
from .routers.heroes import router as heroes
from .routers.maps import router as maps
from .routers.players import router as players
from .routers.roles import router as roles

__all__ = ["gamemodes", "heroes", "maps", "players", "roles"]
