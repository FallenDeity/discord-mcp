import logging

from discord_mcp.core.bot import foo

logger = logging.getLogger(__name__)


def run_server():
    """Run the Discord MCP server."""
    logger.info("Starting Discord MCP server...")
    foo()  # Call the foo function from the bot module
    logger.info("Foo has been called from the server.")
    # TODO: Implement server logic
    raise NotImplementedError("Server logic is not implemented yet.")
