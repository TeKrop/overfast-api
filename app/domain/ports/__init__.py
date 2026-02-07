"""Domain ports (protocols) for dependency injection"""

from .blizzard_client import BlizzardClientPort
from .cache import CachePort
from .storage import StoragePort
from .task_queue import TaskQueuePort

__all__ = [
    "BlizzardClientPort",
    "CachePort",
    "StoragePort",
    "TaskQueuePort",
]
