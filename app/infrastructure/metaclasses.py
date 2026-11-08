"""Set of metaclasses for the project"""

from typing import Any, ClassVar


class Singleton(type):
    """Singleton class, to be used as metaclass."""

    _instances: ClassVar[dict[type, Any]] = {}

    def __call__[T](cls: type[T], *args: object, **kwargs: object) -> T:
        instances = Singleton._instances
        if cls not in instances:
            instances[cls] = type.__call__(cls, *args, **kwargs)
        return instances[cls]

    @classmethod
    def clear_all(cls) -> None:
        """Clear all singleton instances (used in tests for isolation)."""
        cls._instances.clear()
