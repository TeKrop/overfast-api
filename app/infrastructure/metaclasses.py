"""Set of metaclasses for the project"""

from typing import Any, ClassVar


class Singleton(type):
    """Singleton class, to be used as metaclass."""

    _instances: ClassVar[dict[type, Any]] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def clear_all(cls) -> None:
        """Clear all singleton instances (used in tests for isolation)."""
        cls._instances.clear()
