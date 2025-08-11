from __future__ import annotations

import typing as t

from mcp.types import CallToolRequest

from discord_mcp.core.plugins import DiscordMCPPluginManager
from discord_mcp.core.server.shared.context import DiscordMCPContext
from discord_mcp.utils.enums import RateLimitType

from .models import DiscordUser

if t.TYPE_CHECKING:
    from discord_mcp.core.server.middleware import MiddlewareContext
    from discord_mcp.core.server.resources.manager import DiscordMCPResourceTemplate


user_tools_manager = DiscordMCPPluginManager(name="user-tools")


def has_bot_user(ctx: MiddlewareContext[CallToolRequest]) -> bool:
    return ctx.context.bot.user is not None


def is_bot_id(bot_id: int):
    original = user_tools_manager.check(has_bot_user).__predicate__

    async def extended_check(ctx: MiddlewareContext[CallToolRequest]):
        return await original(ctx) and ctx.context.bot.user.id == bot_id  # type: ignore Already verified in check

    return user_tools_manager.check(extended_check)


@user_tools_manager.register_tool
@user_tools_manager.check(has_bot_user)
@is_bot_id(1)
async def get_current_user(ctx: DiscordMCPContext) -> DiscordUser:
    """Get the current bot user."""
    return DiscordUser.from_discord_user(ctx.bot.user)  # type: ignore Already verified in check


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
