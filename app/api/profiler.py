"""Profiler middleware registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.api.enums import Profiler
from app.api.middlewares import (
    MemrayInMemoryMiddleware,
    ObjGraphMiddleware,
    PyInstrumentMiddleware,
    TraceMallocMiddleware,
)
from app.infrastructure.logger import logger

if TYPE_CHECKING:
    from fastapi import FastAPI

_SUPPORTED_PROFILERS = {
    Profiler.MEMRAY: MemrayInMemoryMiddleware,
    Profiler.PYINSTRUMENT: PyInstrumentMiddleware,
    Profiler.TRACEMALLOC: TraceMallocMiddleware,
    Profiler.OBJGRAPH: ObjGraphMiddleware,
}


def register_profiler(app: FastAPI, profiler: str) -> None:  # pragma: no cover
    """Add the requested profiler middleware to the app, or exit if unsupported."""
    if profiler not in _SUPPORTED_PROFILERS:
        logger.error(
            "%s is not a supported profiler, please use one of the following : %s",
            profiler,
            ", ".join(Profiler),
        )
        raise SystemExit

    logger.info("Profiling is enabled with %s", profiler)
    app.add_middleware(_SUPPORTED_PROFILERS[profiler])  # type: ignore[arg-type]
