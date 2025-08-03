import logging
import sys
import typing as t
from types import TracebackType

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

from discord_mcp.utils.enums import ErrorCodes

__all__: tuple[str, ...] = (
    "handle_exception",
    "BaseMcpError",
    "ParseError",
    "InvalidRequestError",
    "InvalidParamsError",
    "InternalError",
    "MethodNotFoundError",
    "ResourceNotFoundError",
    "ResourceReadError",
    "PromptNotFoundError",
    "PromptRenderError",
)


logger = logging.getLogger(__name__)


def handle_exception(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType) -> None:
    """Handle exceptions by logging them."""
    if issubclass(exc_type, KeyboardInterrupt):
        # If the exception is a KeyboardInterrupt, we don't want to log it
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


class BaseMcpError(McpError):
    """Base class for MCP-related errors."""

    def __init__(self, error: ErrorData):
        super().__init__(error)
        self.data = error.data


class ParseError(BaseMcpError):
    """Raised when there is a parse error in the MCP protocol."""

    def __init__(self, message: str = "Error parsing the JSON-RPC request", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.PARSE_ERROR, message=message, data=data))


class InvalidRequestError(BaseMcpError):
    """Raised when the request is invalid in the MCP protocol."""

    def __init__(self, message: str = "Invalid request format", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.INVALID_REQUEST, message=message, data=data))


class InvalidParamsError(BaseMcpError):
    """Raised when the parameters in the request are invalid."""

    def __init__(self, message: str = "Invalid parameters provided", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.INVALID_PARAMS, message=message, data=data))


class InternalError(BaseMcpError):
    """Raised when there is an internal error in the MCP protocol."""

    def __init__(self, message: str = "Internal server error", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.INTERNAL_ERROR, message=message, data=data))


class MethodNotFoundError(BaseMcpError):
    """Raised when a method is not found in the MCP protocol."""

    def __init__(self, message: str = "Requested method not found", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.METHOD_NOT_FOUND, message=message, data=data))


class ResourceNotFoundError(BaseMcpError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Requested resource not found", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.RESOURCE_NOT_FOUND, message=message, data=data))


class ResourceReadError(BaseMcpError):
    """Raised when there is an error reading a resource."""

    def __init__(self, message: str = "Error reading resource", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.RESOURCE_READ_ERROR, message=message, data=data))


class PromptNotFoundError(BaseMcpError):
    """Raised when a requested prompt is not found."""

    def __init__(self, message: str = "Requested prompt not found", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.PROMPT_NOT_FOUND, message=message, data=data))


class PromptRenderError(BaseMcpError):
    """Raised when there is an error rendering a prompt."""

    def __init__(self, message: str = "Error rendering prompt", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.PROMPT_RENDER_ERROR, message=message, data=data))


class DisabledError(BaseMcpError):
    """Raised when a feature is disabled."""

    def __init__(self, message: str = "This feature is currently disabled", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.DISABLED, message=message, data=data))


class RateLimitExceededError(BaseMcpError):
    """Raised when the rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.RATE_LIMIT_EXCEEDED, message=message, data=data))


class PermissionDeniedError(BaseMcpError):
    """Raised when permission is denied."""

    def __init__(self, message: str = "Permission denied", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.PERMISSION_DENIED, message=message, data=data))


class CheckFailureError(BaseMcpError):
    """Raised when a check fails."""

    def __init__(self, message: str = "Check failed", data: t.Any | None = None) -> None:
        super().__init__(error=ErrorData(code=ErrorCodes.CHECK_FAILURE, message=message, data=data))
