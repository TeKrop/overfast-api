"""Set of metaclasses for the project"""
from typing import ClassVar


class Singleton(type):
    """Singleton class, to be used as metaclass."""

    _instances: ClassVar[dict] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
