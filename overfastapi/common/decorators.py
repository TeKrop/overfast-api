"""Decorators module"""
from functools import wraps
from typing import Callable

from fastapi import BackgroundTasks, Request
from pydantic import ValidationError

from overfastapi.common.helpers import overfast_internal_error


def validation_error_handler(response_model: type):
    """Decorator used for checking if the value processed by parsers are valid and
    matches the pydantic model. It prevents FastAPI to immediatly return an error,
    and allows to expose a custom error to the user and send a Discord
    notification to the developer.
    """

    def validation_error_handler_inner(func: Callable):
        @wraps(func)
        async def wrapper(
            background_tasks: BackgroundTasks, request: Request, *args, **kwargs
        ):
            try:
                result = await func(background_tasks, request, *args, **kwargs)
                return (
                    [response_model(**res) for res in result]
                    if isinstance(result, list)
                    else response_model(**result)
                )
            except ValidationError as error:
                raise overfast_internal_error(request.url.path, error) from error

        return wrapper

    return validation_error_handler_inner
