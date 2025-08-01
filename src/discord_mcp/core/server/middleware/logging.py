from __future__ import annotations

import logging
import time
import typing as t

import pydantic_core
from mcp.types import Request, Result

from discord_mcp.utils.logger import add_to_log_context

from .middleware import CallNext, Middleware, MiddlewareContext

logger = logging.getLogger(__name__)


__all__: tuple[str, ...] = ("RequestLoggingMiddleware",)


class RequestLoggingMiddleware(Middleware):
    async def on_request(
        self, ctx: MiddlewareContext[Request[t.Any, t.Any]], call_next: CallNext[Request[t.Any, t.Any], Result]
    ) -> Result:
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
            except Exception:
                logger.exception("Unhandled exception during request")
                raise

            duration = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds
            response_data = {"result": pydantic_core.to_jsonable_python(response), "duration": f"{duration:.2f}ms"}
            logger.info("Request completed", extra=response_data)

            return response
