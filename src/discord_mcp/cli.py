import argparse
import importlib.metadata
import logging
import platform
import sys

from discord_mcp.core.server import run_server
from discord_mcp.utils.exceptions import handle_exception
from discord_mcp.utils.logger import setup_logging

# Set the exception hook to handle uncaught exceptions
sys.excepthook = handle_exception


logger = logging.getLogger(__name__)


def show_version() -> None:
    """Show the version of the application."""
    try:
        version = importlib.metadata.version("discord-mcp")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"

    print(f"discord-mcp version: {version}")
    print(f"Python version: {platform.python_version()}")
    uname = platform.uname()
    print(f"System: {uname.system} {uname.release} {uname.version}")
    print(f"Machine: {uname.machine}")
    print(f"Processor: {uname.processor}")
    print(f"Platform: {platform.platform()}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Discord MCP CLI")
    parser.add_argument("--version", action="store_true", help="Show the version of the application")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--file-logging", action="store_true", help="Enable file logging")
    parser.add_argument("--filename", type=str, default="discord-mcp.log", help="Log file name")

    return parser.parse_args()


def cli_main() -> None:
    """Main function for the CLI."""
    args = parse_args()

    if args.version:
        show_version()
        return

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level, file_logging=args.file_logging, filename=args.filename)
    logger.info("Starting discord-mcp CLI")
    logger.debug("Debug logging is enabled" if args.debug else "Debug logging is disabled")
    logger.info(f"Log file: {args.filename}" if args.file_logging else "File logging is disabled")

    # TODO: Add more CLI commands and functionality here
    logger.warning("CLI is running. Add your commands here.")

    run_server()  # Placeholder for server logic
