import logging
import sys
from types import TracebackType

from mcp.server.fastmcp.exceptions import FastMCPError

__all__: tuple[str, ...] = (
    "handle_exception",
    "PromptError",
)


logger = logging.getLogger(__name__)


def handle_exception(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType) -> None:
    """Handle exceptions by logging them."""
    if issubclass(exc_type, KeyboardInterrupt):
        # If the exception is a KeyboardInterrupt, we don't want to log it
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


class PromptError(FastMCPError):
    """Error in prompt operations."""
