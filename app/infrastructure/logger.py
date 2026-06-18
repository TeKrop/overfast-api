"""Custom Logger Using Loguru, inspired by Riki-1mg gist custom_logging.py"""

import logging
import sys
from pathlib import Path

from loguru import logger as loguru_logger

from app.config import settings


class InterceptHandler(logging.Handler):
    """InterceptionHandler class used to intercept python logs in order
    to transform them into loguru logs.
    """

    def emit(self, record):  # pragma: no cover
        try:
            level = logger.level(record.levelname).name
        except AttributeError:
            level = logging.getLevelName(record.levelno)

        frame, depth = logging.currentframe(), 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def _setup_logger():
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan> - <level>{message}</level>"
    )
    loguru_logger.remove()
    loguru_logger.add(
        sys.stdout,
        enqueue=True,
        backtrace=True,
        level=settings.log_level.upper(),
        format=log_format,
    )
    loguru_logger.add(
        str(Path(settings.logs_root_path) / "access.log"),
        rotation="1 day",
        retention="1 year",
        compression="gz",
        enqueue=True,
        backtrace=True,
        level=settings.log_level.upper(),
        format=log_format,
    )
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    for _log in ("uvicorn", "uvicorn.error", "fastapi"):
        logging.getLogger(_log).handlers = [InterceptHandler()]
    return loguru_logger.bind(method=None)


logger = _setup_logger()
