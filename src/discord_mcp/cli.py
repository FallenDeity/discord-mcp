import asyncio
import importlib.metadata
import logging
import pathlib
import platform
import sys

import click

from discord_mcp.core.bot import Bot
from discord_mcp.core.server.http_server import run_server as run_http_server
from discord_mcp.core.server.stdio_server import run_server as run_stdio_server
from discord_mcp.utils.enums import ServerType
from discord_mcp.utils.exceptions import handle_exception
from discord_mcp.utils.logger import setup_all_logging  # , setup_logging

__all__: tuple[str, ...] = (
    "cli",
    "cli_main",
    "get_version",
    "show_version",
)


# Set the exception hook to handle uncaught exceptions
sys.excepthook = handle_exception

logger = logging.getLogger(__name__)


def get_version() -> str:
    """Get the version of the application."""
    try:
        return importlib.metadata.version("discord-mcp")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--file-logging", is_flag=True, help="Enable file logging")
@click.option("--filename", default="discord-mcp", help="Log file name")
@click.option("--log-dir", type=click.Path(path_type=pathlib.Path), default="logs", help="Log directory")
@click.option("--server-type", type=click.Choice(ServerType), default=ServerType.STDIO, help="Server type to run")
@click.option("--version", is_flag=True, help="Show version information")
@click.pass_context
def cli(
    ctx: click.Context,
    debug: bool,
    file_logging: bool,
    filename: str,
    log_dir: pathlib.Path,
    server_type: str,
    version: bool,
) -> None:
    """Discord MCP CLI - A Model Context Protocol server for Discord integration."""

    # Setup logging early
    # setup_logging(
    #     level=logging.DEBUG if debug else logging.INFO,
    #     file_logging=file_logging,
    #     filename=filename,
    #     log_dir=log_dir,
    # )
    setup_all_logging()

    if version:
        show_version()
        ctx.exit()

    # If no subcommand is provided, run the server
    if ctx.invoked_subcommand is None:
        logger.info("Starting discord-mcp CLI")
        logger.debug("Debug logging is enabled" if debug else "Debug logging is disabled")
        logger.info(f"Server type: {server_type}")

        # Create the bot instance
        bot = Bot(logging_level=logging.DEBUG if debug else logging.INFO, file_logging=file_logging)

        # Run the appropriate server based on server_type
        if server_type == ServerType.HTTP:
            logger.info("Starting HTTP server")
            run_http_server(bot)
        else:
            logger.info("Starting stdio server")
            asyncio.run(run_stdio_server(bot))


def show_version() -> None:
    """Show detailed version and system information."""
    version = get_version()

    click.echo(f"discord-mcp version: {version}")
    click.echo(f"Python version: {platform.python_version()}")

    uname = platform.uname()
    click.echo(f"System: {uname.system} {uname.release} {uname.version}")
    click.echo(f"Machine: {uname.machine}")
    click.echo(f"Processor: {uname.processor}")
    click.echo(f"Platform: {platform.platform()}")


def cli_main() -> None:
    """Main entry point for the CLI."""
    cli()
