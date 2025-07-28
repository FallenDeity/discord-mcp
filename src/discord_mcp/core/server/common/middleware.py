import logging
import time
import typing as t
import uuid
from contextlib import suppress

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from discord_mcp.utils.logger import add_to_log_context

__all__: tuple[str, ...] = ("RequestLoggingMiddleware",)


logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: t.Callable[[Request], t.Awaitable[Response]],
    ) -> Response:
        request_id = self._get_request_id(request)
        correlation_id = request.headers.get("X-Correlation-ID", request_id)
        start_time = time.perf_counter()

        request_metadata = await self._gather_request_metadata(request, request_id, correlation_id)

        with add_to_log_context(**request_metadata):
            logger.info(f"{request.method} {request.url.path} ← {request_metadata['client_ip']}")
            try:
                response = await call_next(request)
            except Exception:
                logger.exception("Unhandled exception during request")
                raise

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id

            self._log_response_metadata(request, response, request_id, correlation_id, start_time)

            return response

    def _get_request_id(self, request: Request) -> str:
        return request.headers.get("X-Request-ID", str(uuid.uuid4()))

    async def _gather_request_metadata(
        self, request: Request, request_id: str, correlation_id: str
    ) -> dict[str, t.Any]:
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")

        payload = None
        if request.method in ("POST", "PUT", "PATCH"):
            with suppress(Exception):
                payload = await request.json()

        return {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "payload": payload,
        }

    def _log_response_metadata(
        self,
        request: Request,
        response: Response,
        request_id: str,
        correlation_id: str,
        start_time: float,
    ) -> None:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        metadata = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "method": request.method,
            "path": request.url.path,
        }
        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} ({duration_ms} ms)",
            extra=metadata,
        )
