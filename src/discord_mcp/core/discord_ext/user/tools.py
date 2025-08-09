from __future__ import annotations

import typing as t

from discord_mcp.core.plugins import DiscordMCPPluginManager
from discord_mcp.core.server.shared.context import DiscordMCPContext
from discord_mcp.utils.enums import RateLimitType

if t.TYPE_CHECKING:
    from discord_mcp.core.server.resources.manager import DiscordMCPResourceTemplate


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
async def get_user_resource(ctx: DiscordMCPContext, user_id: str) -> DiscordUser:
    """Get a user resource by their ID."""
    user = ctx.bot.get_user(int(user_id)) or await ctx.bot.fetch_user(int(user_id))
    return DiscordUser.from_discord_user(user)


@get_user_resource.autocomplete("user_id")
async def autocomplete_user_id(
    ctx: DiscordMCPContext, ref: DiscordMCPResourceTemplate, query: str, context_args: dict[str, t.Any] | None = None
) -> list[str]:
    """Autocomplete user IDs."""
    if not query:
        return []
    users = ctx.bot.users
    return [str(user.id) for user in users if query.lower() in user.name.lower() or query in str(user.id)][:10]


@user_tools_manager.register_tool
@user_tools_manager.limit(RateLimitType.FIXED_WINDOW, rate=1, per=180)
async def get_latency(ctx: DiscordMCPContext) -> float:
    """Get the latency of the bot."""
    latency = ctx.bot.latency * 1000
    return latency
