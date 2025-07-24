import importlib.metadata
import logging
import platform
import sys
from pathlib import Path

import click

from discord_mcp.core.server import run_server
from discord_mcp.utils.exceptions import handle_exception
from discord_mcp.utils.logger import setup_logging

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
@click.option("--log-dir", type=click.Path(path_type=Path), default="logs", help="Log directory")
@click.option("--version", is_flag=True, help="Show version information")
@click.pass_context
def cli(
    ctx: click.Context,
    debug: bool,
    file_logging: bool,
    filename: str,
    log_dir: Path,
    version: bool,
) -> None:
    """Discord MCP CLI - A Model Context Protocol server for Discord integration."""

    # Setup logging early
    setup_logging(
        level=logging.DEBUG if debug else logging.INFO,
        file_logging=file_logging,
        filename=filename,
        log_dir=log_dir,
    )

    if version:
        show_version()
        ctx.exit()

    # If no subcommand is provided, run the server
    if ctx.invoked_subcommand is None:
        logger.info("Starting discord-mcp CLI")
        logger.debug("Debug logging is enabled" if debug else "Debug logging is disabled")

        # TODO: Add more CLI commands and functionality here
        logger.warning("CLI is running. Add your commands here.")

        run_server()


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
