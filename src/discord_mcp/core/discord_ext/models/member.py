from __future__ import annotations

import datetime

import discord
import pydantic

from .user import AvatarDecorationData, User

__all__: tuple[str, ...] = (
    "PartialMember",
    "Member",
    "MemberWithUser",
    "OptionalMemberWithUser",
    "UserWithMember",
)


class PartialMember(pydantic.BaseModel):
    roles: list[str] = pydantic.Field(default_factory=list[str], description="A list of role IDs that the member has.")
    joined_at: datetime.datetime | None = pydantic.Field(
        default=None, description="The timestamp when the member joined the guild, null if guest user."
    )
    deaf: bool = pydantic.Field(description="Whether the member is deafened in voice channels.")
    mute: bool = pydantic.Field(description="Whether the member is muted in voice channels.")
    flags: list[str] = pydantic.Field(description="The flags for the member.")

    @classmethod
    def from_discord_member(cls, member: discord.Member) -> PartialMember:
        """Create a `PartialMember` instance from a `discord.Member` instance."""
        return cls(
            roles=[str(role.id) for role in member.roles if role.id != member.guild.id],
            joined_at=member.joined_at,
            deaf=member.voice.deaf if member.voice else False,
            mute=member.voice.mute if member.voice else False,
            flags=[name for name, value in member.flags if value],
        )


class Member(PartialMember):
    avatar: str | None = pydantic.Field(
        default=None, description="The URL of the member's guild-specific avatar, if set."
    )
    user: User | None = pydantic.Field(default=None, description="The user associated with the member.")
    nick: str | None = pydantic.Field(default=None, description="The nickname of the member, if set.")
    premium_since: datetime.datetime | None = pydantic.Field(
        default=None, description="The timestamp when the member started boosting the guild, if any."
    )
    pending: bool | None = pydantic.Field(
        default=None, description="Whether the member has passed the guild's membership screening requirements."
    )
    permissions: list[str] | None = pydantic.Field(
        default=None,
        description="The total permissions of the member in the channel, including overwrites, if in a channel context.",
    )
    communication_disabled_until: datetime.datetime | None = pydantic.Field(
        default=None,
        description="The timestamp until which the member is communication disabled (timeout), null if not timed out.",
    )
    banner: str | None = pydantic.Field(default=None, description="The URL of the member's banner, if set.")
    avatar_decoration_data: AvatarDecorationData | None = pydantic.Field(
        default=None, description="The member's avatar decoration data, if available."
    )

    @classmethod
    def from_discord_member(cls, member: discord.Member) -> Member:
        """Create a `Member` instance from a `discord.Member` instance."""
        return cls(
            **PartialMember.from_discord_member(member).model_dump(),
            avatar=member.guild_avatar.url if member.guild_avatar else None,
            user=User.from_discord_user(member) if member else None,
            nick=member.nick,
            premium_since=member.premium_since,
            pending=member.pending if hasattr(member, "pending") else None,
            permissions=[name for name, value in member.guild_permissions if value],
            communication_disabled_until=member.timed_out_until,
            banner=member.banner.url if member.banner else None,
            avatar_decoration_data=(
                AvatarDecorationData(asset=member.avatar_decoration.url, sku_id=member.avatar_decoration_sku_id)
                if member.avatar_decoration
                else None
            ),
        )


class OptionalMemberWithUser(PartialMember):
    avatar: str | None = pydantic.Field(
        default=None, description="The URL of the member's guild-specific avatar, if set."
    )
    nick: str | None = pydantic.Field(default=None, description="The nickname of the member, if set.")
    premium_since: datetime.datetime | None = pydantic.Field(
        default=None, description="The timestamp when the member started boosting the guild, if any."
    )
    pending: bool | None = pydantic.Field(
        default=None, description="Whether the member has passed the guild's membership screening requirements."
    )
    permissions: list[str] = pydantic.Field(
        description="The total permissions of the member in the channel, including overwrites, if in a channel context."
    )
    communication_disabled_until: datetime.datetime | None = pydantic.Field(
        default=None,
        description="The timestamp until which the member is communication disabled (timeout), null if not timed out.",
    )
    avatar_decoration_data: AvatarDecorationData | None = pydantic.Field(
        default=None, description="The member's avatar decoration data, if available."
    )

    @classmethod
    def from_discord_member(cls, member: discord.Member) -> OptionalMemberWithUser:
        """Create a `OptionalMemberWithUser` instance from a `discord.Member` instance."""
        return cls(
            **PartialMember.from_discord_member(member).model_dump(),
            avatar=member.guild_avatar.url if member.guild_avatar else None,
            nick=member.nick,
            premium_since=member.premium_since,
            pending=member.pending if hasattr(member, "pending") else None,
            permissions=[name for name, value in member.guild_permissions if value],
            communication_disabled_until=member.timed_out_until,
            avatar_decoration_data=(
                AvatarDecorationData(asset=member.avatar_decoration.url, sku_id=member.avatar_decoration_sku_id)
                if member.avatar_decoration
                else None
            ),
        )


class MemberWithUser(OptionalMemberWithUser):
    user: User = pydantic.Field(description="The user associated with the member.")

    @classmethod
    def from_discord_member(cls, member: discord.Member) -> MemberWithUser:
        """Create a `MemberWithUser` instance from a `discord.Member` instance."""
        return cls(
            **OptionalMemberWithUser.from_discord_member(member).model_dump(),
            user=User.from_discord_user(member),
        )


class UserWithMember(User):
    member: OptionalMemberWithUser = pydantic.Field(description="The member information associated with the user.")

    @classmethod
    def from_discord_member(cls, member: discord.Member) -> UserWithMember:
        """Create a `UserWithMember` instance from a `discord.Member` instance."""
        return cls(
            **User.from_discord_user(member).model_dump(),
            member=OptionalMemberWithUser.from_discord_member(member),
        )
