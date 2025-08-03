from __future__ import annotations

import json
import logging
import time
import typing as t

import pydantic_core
from mcp.shared.exceptions import McpError
from mcp.types import Notification, Request, Result

from discord_mcp.utils.enums import MiddlewareEventTypes
from discord_mcp.utils.exceptions import (
    CheckFailureError,
    InternalError,
    InvalidParamsError,
    ParseError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ResourceReadError,
)
from discord_mcp.utils.logger import add_to_log_context

from .middleware import CallNext, Middleware, MiddlewareContext

logger = logging.getLogger(__name__)


__all__: tuple[str, ...] = ("LoggingMiddleware",)


class LoggingMiddleware(Middleware):
    def _process_exception(
        self, ctx: MiddlewareContext[Request[t.Any, t.Any] | Notification[t.Any, t.Any]], exception: Exception
    ) -> McpError:
        if isinstance(exception, McpError):
            return exception

        base_message = f"Unhandled exception in {ctx.event_type}:{ctx.method}"
        message_data = pydantic_core.to_jsonable_python(ctx.message)

        if isinstance(exception, (ValueError, TypeError)):
            return InvalidParamsError(f"{base_message}\n Invalid parameters provided: {exception}", data=message_data)
        if isinstance(exception, (json.JSONDecodeError, pydantic_core.ValidationError, UnicodeDecodeError)):
            return ParseError(f"{base_message}\n Error parsing the request: {exception}", data=message_data)
        if isinstance(exception, (FileNotFoundError, KeyError)):
            return ResourceNotFoundError(f"{base_message}\n Resource not found: {exception}", data=message_data)
        if isinstance(exception, (OSError, IOError, IsADirectoryError)):
            return ResourceReadError(f"{base_message}\n Resource read error: {exception}", data=message_data)
        if isinstance(exception, PermissionError):
            return PermissionDeniedError(f"{base_message}\n Permission denied: {exception}", data=message_data)
        if isinstance(exception, AssertionError):
            return CheckFailureError(f"{base_message}\n Check failed: {exception}", data=message_data)
        return InternalError(f"{base_message}\n Internal error: {exception}", data=message_data)

    async def on_message(
        self,
        ctx: MiddlewareContext[Request[t.Any, t.Any] | Notification[t.Any, t.Any]],
        call_next: CallNext[Request[t.Any, t.Any] | Notification[t.Any, t.Any], Result | None],
    ) -> Result | None:
        start_time = time.perf_counter()
        request_data = {
            "method": ctx.method,
            "event_type": ctx.event_type,
            "timestamp": ctx.timestamp.isoformat(),
            "payload": pydantic_core.to_jsonable_python(ctx.message),
        }

        with add_to_log_context(**request_data):
            try:
                response = await call_next(ctx)
            except Exception as e:
                error = self._process_exception(ctx, e)
                logger.exception(f"Unhandled exception of {type(e).__name__} in {ctx.event_type}:{ctx.method}")
                raise error from e

            duration = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds
            response_data = {"result": pydantic_core.to_jsonable_python(response), "duration": f"{duration:.2f}ms"}
            logger.info(
                "Request completed" if ctx.event_type == MiddlewareEventTypes.REQUEST else "Notification processed",
                extra=response_data,
            )

            return response
