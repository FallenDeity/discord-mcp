from __future__ import annotations

import datetime
import enum
import typing as t

import discord
import pydantic

from .appinfo import PartialAppInfo
from .channel import PartialChannel
from .guild import GuildPreviewWithCounts, InviteGuild
from .scheduled_event import GuildScheduledEvent, _discord_scheduled_event_to_pydantic
from .user import PartialUser

__all__: tuple[str, ...] = (
    "InviteType",
    "InviteTargetType",
    "InviteMetadata",
    "VanityInvite",
    "BaseInvite",
    "Invite",
    "InviteWithCounts",
    "InviteCreationOptions",
)


class InviteType(enum.StrEnum):
    GUILD = "guild"
    GROUP_DM = "group_dm"
    FRIEND = "friend"

    @classmethod
    def from_discord_invite_type(cls, invite_type: t.Literal[0, 1, 2]) -> InviteType:
        return {0: cls.GUILD, 1: cls.GROUP_DM, 2: cls.FRIEND}.get(invite_type, cls.GUILD)


class InviteTargetType(enum.StrEnum):
    UNKNOWN = "unknown"
    STREAM = "stream"
    EMBEDDED_APPLICATION = "embedded_application"

    @classmethod
    def from_discord_invite_target_type(cls, target_type: t.Literal[0, 1, 2]) -> InviteTargetType:
        return {0: cls.UNKNOWN, 1: cls.STREAM, 2: cls.EMBEDDED_APPLICATION}.get(target_type, cls.UNKNOWN)


class InviteMetadata(pydantic.BaseModel):
    uses: int = pydantic.Field(description="Number of times this invite has been used.")
    max_uses: int = pydantic.Field(description="Maximum number of times this invite can be used.")
    max_age: int = pydantic.Field(description="Duration (in seconds) after which the invite expires.")
    temporary: bool = pydantic.Field(description="Whether the invite grants temporary membership.")
    created_at: datetime.datetime = pydantic.Field(description="Timestamp when the invite was created.")

    @classmethod
    def from_discord_invite_metadata(cls, invite: discord.Invite) -> InviteMetadata:
        return cls(
            uses=invite.uses or 0,
            max_uses=invite.max_uses or 0,
            max_age=invite.max_age or 0,
            temporary=invite.temporary or False,
            created_at=invite.created_at or datetime.datetime.now(),
        )


class VanityInvite(InviteMetadata):
    code: str | None = pydantic.Field(default=None, description="The vanity URL code for the guild.")
    revoked: bool | None = pydantic.Field(default=None, description="Whether the vanity URL has been revoked.")

    @classmethod
    def from_discord_vanity_invite(cls, invite: discord.Invite) -> VanityInvite:
        return cls(
            **InviteMetadata.from_discord_invite_metadata(invite).model_dump(),
            code=invite.code,
            revoked=invite.revoked,
        )


class BaseInvite(InviteMetadata):
    code: str = pydantic.Field(description="The invite code.")
    channel: PartialChannel | None = pydantic.Field(description="The channel this invite is for.")

    @classmethod
    def from_discord_invite(cls, invite: discord.Invite) -> BaseInvite:
        channel = PartialChannel.from_discord_channel(invite.channel) if isinstance(invite.channel, (discord.abc.GuildChannel, discord.PartialInviteChannel)) else None  # type: ignore
        return cls(
            **InviteMetadata.from_discord_invite_metadata(invite).model_dump(),
            code=invite.code,
            channel=channel,
        )


class Invite(BaseInvite):
    guild: InviteGuild | None = pydantic.Field(default=None, description="The guild this invite is for, if available.")
    inviter: PartialUser | None = pydantic.Field(
        default=None, description="The user who created the invite, if available."
    )
    target_user: PartialUser | None = pydantic.Field(
        default=None, description="The user whose stream to display for this invite, if applicable."
    )
    target_type: InviteTargetType | None = pydantic.Field(
        default=None, description="The type of target for this invite if it is a voice invite, if any."
    )
    target_application: PartialAppInfo | None = pydantic.Field(
        default=None, description="The embedded application to open for this invite, if any."
    )
    guild_scheduled_event: GuildScheduledEvent | None = pydantic.Field(
        default=None, description="The scheduled event associated with this invite, if any."
    )
    type: InviteType = pydantic.Field(description="The type of invite.")
    flags: list[str] | None = pydantic.Field(default=None, description="The invite flags, if any.")
    expires_at: datetime.datetime | None = pydantic.Field(
        default=None, description="The timestamp when the invite expires, if any."
    )

    @classmethod
    def from_discord_invite(cls, invite: discord.Invite) -> Invite:
        """Create an `Invite` instance from a `discord.Invite` instance."""
        guild = (
            InviteGuild.from_discord_guild(invite.guild)
            if isinstance(invite.guild, (discord.Guild, discord.PartialInviteGuild))
            else None
        )
        inviter = PartialUser.from_discord_user(invite.inviter) if invite.inviter else None
        target_user = PartialUser.from_discord_user(invite.target_user) if invite.target_user else None
        target_application = (
            PartialAppInfo.from_discord_appinfo(invite.target_application) if invite.target_application else None
        )
        guild_scheduled_event = (
            _discord_scheduled_event_to_pydantic(invite.scheduled_event) if invite.scheduled_event else None
        )
        return cls(
            **BaseInvite.from_discord_invite(invite).model_dump(),
            guild=guild,
            inviter=inviter,
            target_user=target_user,
            target_type=InviteTargetType.from_discord_invite_target_type(invite.target_type.value),
            target_application=target_application,
            guild_scheduled_event=guild_scheduled_event,
            type=InviteType.from_discord_invite_type(invite.type.value),
            flags=[name for name, value in invite.flags if value] if invite.flags else None,
            expires_at=invite.expires_at,
        )


class InviteWithCounts(Invite, GuildPreviewWithCounts[discord.PartialInviteGuild | discord.Guild]):
    @classmethod
    def from_discord_invite(cls, invite: discord.Invite) -> InviteWithCounts:
        """Create an `InviteWithCounts` instance from a `discord.Invite` instance."""
        return cls(
            **Invite.from_discord_invite(invite).model_dump(),
            **GuildPreviewWithCounts.from_discord_guild(invite.guild).model_dump(),
        )


class InviteCreationOptions(pydantic.BaseModel):
    max_age: int = pydantic.Field(
        default=86400,
        description="Duration (in seconds) after which the invite expires. 0 for never, between 0 and 604800 (7 days).",
    )
    max_uses: int = pydantic.Field(
        default=0, description="Maximum number of times this invite can be used. 0 for unlimited, between 0 and 100."
    )
    temporary: bool = pydantic.Field(
        default=False, description="Whether the invite grants temporary membership. Defaults to False."
    )
    unique: bool = pydantic.Field(
        default=False,
        description="Whether to create a unique invite, i.e don't reuse a similar invite if one exists. Defaults to False.",
    )
    target_type: InviteTargetType | None = pydantic.Field(
        default=None, description="The type of target for this invite if it is a voice invite, if any."
    )
    target_user_id: str | None = pydantic.Field(
        default=None,
        description="The user ID whose stream to display for this invite, required if target_type is STREAM.",
    )
    target_application_id: str | None = pydantic.Field(
        default=None,
        description="The embedded application to open for this invite, required if target_type is EMBEDDED_APPLICATION.",
    )
