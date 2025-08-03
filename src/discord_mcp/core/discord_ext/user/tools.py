from __future__ import annotations

from discord_mcp.core.plugins import DiscordMCPPluginManager
from discord_mcp.core.server.shared.context import DiscordMCPContext

from .models import DiscordUser

user_tools_manager = DiscordMCPPluginManager(name="user-tools")


@user_tools_manager.register_tool
async def get_current_user(ctx: DiscordMCPContext) -> DiscordUser:
    """Get the current bot user."""
    assert ctx.bot.user is not None, "Bot user is not set"
    return DiscordUser.from_discord_user(ctx.bot.user)


@user_tools_manager.register_tool
async def get_user_by_id(ctx: DiscordMCPContext, user_id: str) -> DiscordUser:
    """Get a user by their ID."""
    user = ctx.bot.get_user(int(user_id)) or await ctx.bot.fetch_user(int(user_id))
    return DiscordUser.from_discord_user(user)


@user_tools_manager.register_resource("resource://discord/user/{user_id}")
async def get_user_resource(ctx: DiscordMCPContext, user_id: int) -> DiscordUser:
    """Get a user resource by their ID."""
    user = ctx.bot.get_user(user_id) or await ctx.bot.fetch_user(user_id)
    return DiscordUser.from_discord_user(user)
