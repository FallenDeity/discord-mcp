from __future__ import annotations

import typing as t

import discord

from discord_mcp.core.plugins import DiscordMCPPluginManager
from discord_mcp.core.server.shared.context import DiscordMCPContext

from ..models.channel import Channel, ChannelUpdate, _discord_channel_to_pydantic
from ..models.response import CallToolResponse

# if t.TYPE_CHECKING:
#     from discord_mcp.core.server.middleware import MiddlewareContext
#     from discord_mcp.core.server.resources.manager import DiscordMCPResourceTemplate


channel_manager = DiscordMCPPluginManager(name="channel")


PermissionFlags = list[t.Literal[*list(discord.Permissions.VALID_FLAGS.keys())]]


def _convert_tags(tags: list[dict[str, t.Any]]) -> list[discord.ForumTag]:
    d_tags = [discord.ForumTag(name=tag["name"], moderated=tag["moderated"]) for tag in tags]
    for d_tag, tag in zip(d_tags, tags):
        d_tag.id = int(tag["id"])
    return d_tags


def _process_channel_edit_params(
    update: ChannelUpdate,
) -> dict[str, t.Any]:
    params = update.model_dump(exclude_unset=True)
    for tag_field in ("available_tags", "applied_tags"):
        if tag_field in params:
            params[tag_field] = _convert_tags(params[tag_field])
    if "default_reaction_emoji" in params:
        params["default_reaction_emoji"] = discord.PartialEmoji(**params["default_reaction_emoji"])
    return params


@channel_manager.register_tool
async def get_channel(ctx: DiscordMCPContext, channel_id: str) -> Channel:
    """
    Get a channel by its ID.

    Parameters
    ----------
    ctx : DiscordMCPContext
        The context of the request.
    channel_id : str
        The ID of the channel to retrieve.
    """
    channel = ctx.bot.get_channel(int(channel_id)) or await ctx.bot.fetch_channel(int(channel_id))
    return _discord_channel_to_pydantic(channel)


@channel_manager.register_tool
async def edit_channel(ctx: DiscordMCPContext, channel_id: str, update: ChannelUpdate) -> Channel:
    """
    Edit a channel by its ID.

    Parameters
    ----------
    ctx : DiscordMCPContext
        The context of the request.
    channel_id : str
        The ID of the channel to edit.
    update : ChannelUpdate
        The updates to apply to the channel.
    """
    channel: discord.abc.GuildChannel | discord.abc.PrivateChannel | discord.Thread = ctx.bot.get_channel(
        int(channel_id)
    ) or await ctx.bot.fetch_channel(int(channel_id))
    if isinstance(channel, (discord.abc.GuildChannel, discord.Thread)):
        params = _process_channel_edit_params(update)
        await channel.edit(**params)
        channel = await ctx.bot.fetch_channel(int(channel_id))
        return _discord_channel_to_pydantic(channel)
    raise ValueError("Cannot edit a private channel.")


@channel_manager.register_tool
async def delete_channel(ctx: DiscordMCPContext, channel_id: str, reason: str | None = None) -> CallToolResponse:
    """
    Delete a channel by its ID.

    Parameters
    ----------
    ctx : DiscordMCPContext
        The context of the request.
    channel_id : str
        The ID of the channel to delete.
    reason : str | None
        The reason for deleting the channel.
    """
    channel: discord.abc.GuildChannel | discord.abc.PrivateChannel | discord.Thread = ctx.bot.get_channel(
        int(channel_id)
    ) or await ctx.bot.fetch_channel(int(channel_id))
    if isinstance(channel, (discord.abc.GuildChannel, discord.Thread)):
        await channel.delete(reason=reason)
        return CallToolResponse(message=f"Channel {channel_id} deleted.")
    raise ValueError("Cannot delete a private channel.")


@channel_manager.register_tool
async def edit_channel_permissions(
    ctx: DiscordMCPContext,
    channel_id: str,
    target_id: str,
    target_type: t.Literal["role", "member"],
    allow: PermissionFlags | None = None,
    deny: PermissionFlags | None = None,
) -> CallToolResponse:
    """
    Edit the permissions of a channel by its ID.

    Parameters
    ----------
    ctx : DiscordMCPContext
        The context of the request.
    channel_id : str
        The ID of the channel to edit permissions for.
    target_id : str
        The ID of the target (user or role) to edit permissions for.
    type : Literal["role", "member"]
        The type of target (role or member).
    allow : PermissionFlags | None
        The permissions to allow.
    deny : PermissionFlags | None
        The permissions to deny.
    """
    channel: discord.abc.GuildChannel | discord.abc.PrivateChannel | discord.Thread = ctx.bot.get_channel(
        int(channel_id)
    ) or await ctx.bot.fetch_channel(int(channel_id))
    if isinstance(channel, discord.abc.GuildChannel):
        guild = channel.guild
        role_or_member: discord.Role | discord.Member | None = None
        if target_type == "role":
            role_or_member = guild.get_role(int(target_id)) or await guild.fetch_role(int(target_id))
        if target_type == "member":
            role_or_member = guild.get_member(int(target_id)) or await guild.fetch_member(int(target_id))
        if role_or_member is None:
            raise ValueError(f"Target {target_id} not found in guild {guild.id}.")
        overwrite = discord.PermissionOverwrite()
        for perm in allow or []:
            setattr(overwrite, str(perm), True)
        for perm in deny or []:
            setattr(overwrite, str(perm), False)
        await channel.set_permissions(role_or_member, overwrite=overwrite)
        return CallToolResponse(message=f"Channel {channel_id} permissions updated.")
    raise ValueError("Cannot edit permissions of a private channel.")
