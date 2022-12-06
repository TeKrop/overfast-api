"""Custom Logger Using Loguru, inspired by Riki-1mg gist custom_logging.py"""

import logging
import sys
from pathlib import Path

from loguru import logger

from overfastapi.config import LOGS_ROOT_PATH


class InterceptHandler(logging.Handler):
    """InterceptionHandler class used to intercept python logs in order
    to transform them into loguru logs.
    """

    loglevel_mapping = {
        50: "CRITICAL",
        40: "ERROR",
        30: "WARNING",
        20: "INFO",
        10: "DEBUG",
        0: "NOTSET",
    }

    def emit(self, record):  # pragma: no cover
        try:
            level = logger.level(record.levelname).name
        except AttributeError:
            level = self.loglevel_mapping[record.levelno]

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


class OverFastAPILogger:
    @classmethod
    def make_logger(cls):
        return cls.customize_logging(
            f"{LOGS_ROOT_PATH}/access.log",
            level="debug",
            retention="1 year",
            rotation="1 day",
            log_format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan> - <level>{message}</level>"
            ),
        )

    @classmethod
    def customize_logging(
        cls, filepath: Path, level: str, rotation: str, retention: str, log_format: str
    ):
        logger.remove()
        logger.add(
            sys.stdout,
            enqueue=True,
            backtrace=True,
            level=level.upper(),
            format=log_format,
        )
        logger.add(
            str(filepath),
            rotation=rotation,
            retention=retention,
            enqueue=True,
            backtrace=True,
            level=level.upper(),
            format=log_format,
        )
        logging.basicConfig(handlers=[InterceptHandler()], level=0)
        logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
        for _log in ("uvicorn", "uvicorn.error", "fastapi"):
            _logger = logging.getLogger(_log)
            _logger.handlers = [InterceptHandler()]

        return logger.bind(method=None)


# Instanciate generic logger for all the app
logger = OverFastAPILogger.make_logger()
