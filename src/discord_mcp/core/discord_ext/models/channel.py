from __future__ import annotations

import enum
import typing as t

import discord
import pydantic
from discord.channel import CategoryChannel as DiscordCategoryChannel
from discord.channel import DMChannel as DiscordDMChannel
from discord.channel import ForumChannel as DiscordForumChannel
from discord.channel import GroupChannel
from discord.channel import StageChannel as DiscordStageChannel
from discord.channel import TextChannel as DiscordTextChannel
from discord.channel import VoiceChannel as DiscordVoiceChannel
from discord.threads import Thread as DiscordThreadChannel

from .thread import ThreadMember, ThreadMetadata
from .user import PartialUser

__all__: tuple[str, ...] = (
    "ThreadArchiveDuration",
    "ForumOrderType",
    "ForumLayoutType",
    "VideoQualityMode",
    "PermissionOverwrite",
    "OverwriteType",
    "ChannelType",
    "TextChannel",
    "NewsChannel",
    "VoiceChannel",
    "CategoryChannel",
    "StageChannel",
    "ThreadChannel",
    "ForumChannel",
    "MediaChannel",
    "DefaultReaction",
    "ForumTag",
    "DMChannel",
    "GroupChannel",
    "StageInstance",
    "BaseDMChannel",
    "GuildChannel",
    "Channel",
    "BaseChannel",
    "BaseGuildChannel",
    "BaseTextChannel",
    "BaseForumChannel",
    "TextChannelUpdate",
    "AnnouncementChannelUpdate",
    "VoiceChannelUpdate",
    "StageChannelUpdate",
    "ForumChannelUpdate",
    "MediaChannelUpdate",
    "ChannelUpdate",
    "ThreadChannelUpdate",
    "_discord_channel_to_pydantic",
)

BaseChannelT = t.TypeVar("BaseChannelT", bound=discord.abc.GuildChannel | discord.abc.PrivateChannel | discord.Thread)
BaseGuildChannelT = t.TypeVar("BaseGuildChannelT", bound=discord.abc.GuildChannel)
TextChannelT = t.TypeVar("TextChannelT", bound=DiscordTextChannel | DiscordForumChannel)
PrivateChannelT = t.TypeVar("PrivateChannelT", bound=discord.abc.PrivateChannel)

ThreadArchiveDuration = t.Literal[60, 1440, 4320, 10080]


class ForumOrderType(enum.StrEnum):
    LATEST_ACTIVITY = "latest_activity"
    CREATION_DATE = "creation_date"


class ForumLayoutType(enum.StrEnum):
    NOT_SET = "not_set"
    LIST_VIEW = "list_view"
    GALLERY_VIEW = "gallery_view"


class VideoQualityMode(enum.StrEnum):
    AUTO = "auto"
    FULL_HD = "full_hd"


class OverwriteType(enum.StrEnum):
    ROLE = "role"
    MEMBER = "member"


class ChannelType(enum.StrEnum):
    GUILD_TEXT = "guild_text"
    DM = "dm"
    GUILD_VOICE = "guild_voice"
    GROUP_DM = "group_dm"
    GUILD_CATEGORY = "guild_category"
    GUILD_ANNOUNCEMENT = "guild_announcement"
    ANNOUNCEMENT_THREAD = "announcement_thread"
    PUBLIC_THREAD = "public_thread"
    PRIVATE_THREAD = "private_thread"
    GUILD_STAGE_VOICE = "guild_stage_voice"
    GUILD_DIRECTORY = "guild_directory"
    GUILD_FORUM = "guild_forum"
    GUILD_MEDIA = "guild_media"


class PermissionOverwrite(pydantic.BaseModel):
    id: str = pydantic.Field(description="The ID of the role or user.")
    type: OverwriteType = pydantic.Field(description="The type of the overwrite. 0 for role, 1 for member.")
    allow: list[str] = pydantic.Field(default_factory=list, description="List of key names of allowed permissions.")
    deny: list[str] = pydantic.Field(default_factory=list, description="List of key names of denied permissions.")


class BaseChannel(pydantic.BaseModel, t.Generic[BaseChannelT]):
    id: str = pydantic.Field(description="The unique ID of the channel.")
    name: str = pydantic.Field(description="The name of the channel.")

    @classmethod
    def from_discord_channel(cls, channel: BaseChannelT) -> BaseChannel[BaseChannelT]:
        """Create a BaseChannel instance from a discord.abc.GuildChannel or discord.abc.PrivateChannel object."""
        return cls(
            id=str(channel.id),
            name=getattr(channel, "name", ""),
        )


class BaseGuildChannel(BaseChannel[BaseGuildChannelT]):
    guild_id: str = pydantic.Field(description="The ID of the guild this channel belongs to.")
    position: int = pydantic.Field(description="The position of the channel in the guild's channel list.")
    permission_overwrites: list[PermissionOverwrite] = pydantic.Field(
        description="List of permission overwrites for the channel."
    )
    nsfw: bool = pydantic.Field(default=False, description="Whether the channel is marked as NSFW.")
    parent_id: str | None = pydantic.Field(default=None, description="The ID of the parent category, if any.")

    @classmethod
    def from_discord_channel(cls, channel: BaseGuildChannelT) -> BaseGuildChannel[BaseGuildChannelT]:
        """Create a BaseGuildChannel instance from a discord.abc.GuildChannel object."""
        return cls(
            **BaseChannel.from_discord_channel(channel).model_dump(),
            guild_id=str(channel.guild.id),
            position=channel.position,
            permission_overwrites=[
                PermissionOverwrite(
                    id=str(role_or_member.id),
                    type=OverwriteType.ROLE if isinstance(role_or_member, discord.Role) else OverwriteType.MEMBER,
                    allow=[name for name, value in overwrite if value],
                    deny=[name for name, value in overwrite if not value],
                )
                for role_or_member, overwrite in channel.overwrites.items()
            ],
            nsfw=getattr(channel, "nsfw", False),
            parent_id=str(channel.category_id) if channel.category_id else None,
        )


class BaseTextChannel(BaseGuildChannel[TextChannelT]):
    topic: str | None = pydantic.Field(default=None, description="The topic of the text channel, if any.")
    last_message_id: str | None = pydantic.Field(
        default=None, description="The ID of the last message sent in this channel, if any."
    )
    last_pin_timestamp: str | None = pydantic.Field(
        default=None, description="The timestamp of the last pinned message, if any."
    )
    rate_limit_per_user: int = pydantic.Field(default=0, description="The rate limit per user in seconds.")
    default_thread_rate_limit_per_user: int = pydantic.Field(
        default=0, description="The default rate limit per user for threads created in this channel, if any."
    )
    default_auto_archive_duration: ThreadArchiveDuration = pydantic.Field(
        description="The default auto-archive duration for threads created in this channel. Can be 60, 1440, 4320, or 10080 minutes."
    )

    @classmethod
    def from_discord_channel(cls, channel: TextChannelT) -> BaseTextChannel[TextChannelT]:
        """Create a BaseTextChannel instance from a discord.TextChannel object."""
        return cls(
            **BaseGuildChannel.from_discord_channel(channel).model_dump(),
            topic=channel.topic,
            last_message_id=str(channel.last_message_id) if channel.last_message_id else None,
            last_pin_timestamp=None,
            rate_limit_per_user=channel.slowmode_delay,
            default_thread_rate_limit_per_user=channel.default_thread_slowmode_delay,
            default_auto_archive_duration=channel.default_auto_archive_duration,
        )


class TextChannel(BaseTextChannel[DiscordTextChannel]):
    type: ChannelType = pydantic.Field(default=ChannelType.GUILD_TEXT, description="The type of the channel.")

    @classmethod
    def from_discord_channel(cls, channel: DiscordTextChannel) -> TextChannel:
        """Create a TextChannel instance from a discord.TextChannel object."""
        return cls(**BaseTextChannel.from_discord_channel(channel).model_dump(), type=ChannelType.GUILD_TEXT)


class NewsChannel(BaseTextChannel[DiscordTextChannel]):
    type: ChannelType = pydantic.Field(default=ChannelType.GUILD_ANNOUNCEMENT, description="The type of the channel.")

    @classmethod
    def from_discord_channel(cls, channel: DiscordTextChannel) -> NewsChannel:
        """Create a NewsChannel instance from a discord.TextChannel object."""
        return cls(**BaseTextChannel.from_discord_channel(channel).model_dump(), type=ChannelType.GUILD_ANNOUNCEMENT)


class VoiceChannel(BaseGuildChannel[DiscordVoiceChannel]):
    type: ChannelType = pydantic.Field(default=ChannelType.GUILD_VOICE, description="The type of the channel.")
    bitrate: int = pydantic.Field(description="The bitrate (in bits) of the voice channel.")
    user_limit: int = pydantic.Field(description="The user limit of the voice channel.")
    rtc_region: str | None = pydantic.Field(default=None, description="The RTC region of the voice channel, if any.")
    video_quality_mode: VideoQualityMode = pydantic.Field(
        description="The video quality mode of the voice channel. 1 for auto, 2 for 720p."
    )

    @classmethod
    def from_discord_channel(cls, channel: DiscordVoiceChannel) -> VoiceChannel:
        """Create a VoiceChannel instance from a discord.VoiceChannel object."""
        return cls(
            **BaseGuildChannel.from_discord_channel(channel).model_dump(),
            type=ChannelType.GUILD_VOICE,
            bitrate=channel.bitrate,
            user_limit=channel.user_limit,
            rtc_region=channel.rtc_region,
            video_quality_mode=(
                VideoQualityMode.AUTO
                if channel.video_quality_mode == discord.VideoQualityMode.auto
                else VideoQualityMode.FULL_HD
            ),
        )


class CategoryChannel(BaseGuildChannel[DiscordCategoryChannel]):
    type: ChannelType = pydantic.Field(default=ChannelType.GUILD_CATEGORY, description="The type of the channel.")

    @classmethod
    def from_discord_channel(cls, channel: DiscordCategoryChannel) -> CategoryChannel:
        """Create a CategoryChannel instance from a discord.CategoryChannel object."""
        return cls(
            **BaseGuildChannel.from_discord_channel(channel).model_dump(),
            type=ChannelType.GUILD_CATEGORY,
        )


class StageChannel(BaseGuildChannel[DiscordStageChannel]):
    type: ChannelType = pydantic.Field(default=ChannelType.GUILD_STAGE_VOICE, description="The type of the channel.")
    bitrate: int = pydantic.Field(description="The bitrate (in bits) of the stage channel.")
    user_limit: int = pydantic.Field(description="The user limit of the stage channel.")
    rtc_region: str | None = pydantic.Field(default=None, description="The RTC region of the stage channel, if any.")
    topic: str | None = pydantic.Field(default=None, description="The topic of the stage channel, if any.")

    @classmethod
    def from_discord_channel(cls, channel: DiscordStageChannel) -> StageChannel:
        """Create a StageChannel instance from a discord.StageChannel object."""
        return cls(
            **BaseGuildChannel.from_discord_channel(channel).model_dump(),
            type=ChannelType.GUILD_STAGE_VOICE,
            bitrate=channel.bitrate,
            user_limit=channel.user_limit,
            rtc_region=channel.rtc_region,
            topic=channel.topic,
        )


class ThreadChannel(BaseChannel[discord.Thread]):
    type: ChannelType = pydantic.Field(
        description="The type of the channel. Can be ANNOUNCEMENT_THREAD, PUBLIC_THREAD, or PRIVATE_THREAD."
    )
    guild_id: str = pydantic.Field(description="The ID of the guild this thread belongs to.")
    parent_id: str = pydantic.Field(description="The ID of the parent channel.")
    owner_id: str = pydantic.Field(description="The ID of the user who created the thread.")
    nsfw: bool = pydantic.Field(default=False, description="Whether the thread is marked as NSFW.")
    last_message_id: str | None = pydantic.Field(
        default=None, description="The ID of the last message sent in this thread, if any."
    )
    rate_limit_per_user: int = pydantic.Field(default=0, description="The rate limit per user in seconds.")
    message_count: int = pydantic.Field(description="The approximate number of messages in the thread.")
    member_count: int = pydantic.Field(description="The approximate number of members in the thread.")
    total_message_sent: int = pydantic.Field(description="The total number of messages sent in the thread.")
    thread_metadata: ThreadMetadata = pydantic.Field(description="Thread-specific metadata.")
    member: ThreadMember | None = pydantic.Field(
        default=None, description="Thread member object for the current user, if they are a member of the thread."
    )
    last_pin_timestamp: str | None = pydantic.Field(
        default=None, description="The timestamp of the last pinned message, if any."
    )
    flags: list[str] = pydantic.Field(description="The flags for the thread channel.")
    applied_tags: list[str] = pydantic.Field(
        default_factory=list, description="The applied tags for the thread, if any."
    )

    @classmethod
    def from_discord_channel(cls, channel: DiscordThreadChannel) -> ThreadChannel:
        """Create a ThreadChannel instance from a discord.Thread object."""
        return cls(
            **BaseChannel.from_discord_channel(channel).model_dump(),
            guild_id=str(channel.guild.id),
            parent_id=str(channel.parent.id) if channel.parent else "",
            type=(
                ChannelType.ANNOUNCEMENT_THREAD
                if channel.type == discord.ChannelType.news_thread
                else (
                    ChannelType.PUBLIC_THREAD
                    if channel.type == discord.ChannelType.public_thread
                    else ChannelType.PRIVATE_THREAD
                )
            ),
            owner_id=str(channel.owner_id) if channel.owner_id else "",
            nsfw=channel.is_nsfw(),
            last_message_id=str(channel.last_message_id) if channel.last_message_id else None,
            rate_limit_per_user=channel.slowmode_delay,
            message_count=channel.message_count,
            member_count=channel.member_count,
            total_message_sent=channel.total_message_sent,
            thread_metadata=ThreadMetadata(
                archived=channel.archived,
                auto_archive_duration=t.cast(t.Literal[60, 1440, 4320, 10080], channel.auto_archive_duration),
                archive_timestamp=channel.archive_timestamp.isoformat(),
                locked=channel.locked,
                invitable=channel.invitable if hasattr(channel, "invitable") else None,
                create_timestamp=channel.created_at.isoformat() if channel.created_at else None,
            ),
            member=(
                ThreadMember(
                    id=str(channel.me.id),
                    user_id=str(channel.me.id),
                    join_timestamp=channel.me.joined_at.isoformat() if channel.me and channel.me.joined_at else "",
                    flags=channel.me.flags if channel.me else 0,
                )
                if channel.me
                else None
            ),
            last_pin_timestamp=None,
            flags=[name for name, value in channel.flags if value],
            applied_tags=[tag.name for tag in channel.applied_tags],
        )


class DefaultReaction(pydantic.BaseModel):
    emoji_id: str | None = pydantic.Field(default=None, description="The ID of the emoji, if custom.")
    emoji_name: str | None = pydantic.Field(default=None, description="The name of the emoji.")


class ForumTag(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the tag.")
    name: str = pydantic.Field(description="The name of the tag.")
    moderated: bool = pydantic.Field(description="Whether the tag is moderated.")
    emoji_id: str | None = pydantic.Field(default=None, description="The ID of the emoji for the tag, if custom.")
    emoji_name: str | None = pydantic.Field(default=None, description="The name of the emoji for the tag.")


class BaseForumChannel(BaseTextChannel[DiscordForumChannel]):
    available_tags: list[ForumTag] = pydantic.Field(
        default_factory=list[ForumTag], description="List of available tags for the forum channel."
    )
    default_reaction_emoji: DefaultReaction | None = pydantic.Field(
        default=None, description="The default reaction emoji for posts in the forum channel, if any."
    )
    default_sort_order: ForumOrderType | None = pydantic.Field(
        default=None,
        description="The default sort order for posts in the forum channel, if any. 0 for latest activity, 1 for creation date.",
    )
    default_forum_layout: ForumLayoutType | None = pydantic.Field(
        default=None,
        description="The default layout for the forum channel, if any. 0 for no default set, 1 for list view, 2 for gallery view.",
    )
    flags: list[str] = pydantic.Field(description="The flags for the forum channel.")

    @classmethod
    def from_discord_channel(cls, channel: DiscordForumChannel) -> BaseForumChannel:
        """Create a BaseForumChannel instance from a discord.ForumChannel object."""
        return cls(
            **BaseTextChannel.from_discord_channel(channel).model_dump(),
            available_tags=[
                ForumTag(
                    id=str(tag.id),
                    name=tag.name,
                    moderated=tag.moderated,
                    emoji_id=str(tag.emoji.id) if tag.emoji and tag.emoji.id else None,
                    emoji_name=tag.emoji.name if tag.emoji else None,
                )
                for tag in channel.available_tags
            ],
            default_reaction_emoji=(
                DefaultReaction(
                    emoji_id=(
                        str(channel.default_reaction_emoji.id)
                        if channel.default_reaction_emoji and channel.default_reaction_emoji.id
                        else None
                    ),
                    emoji_name=channel.default_reaction_emoji.name if channel.default_reaction_emoji else None,
                )
                if channel.default_reaction_emoji
                else None
            ),
            default_sort_order=(
                ForumOrderType.LATEST_ACTIVITY
                if channel.default_sort_order == discord.ForumOrderType.latest_activity
                else ForumOrderType.CREATION_DATE
            ),
            default_forum_layout=(
                ForumLayoutType.GALLERY_VIEW
                if channel.default_layout == discord.ForumLayoutType.gallery_view
                else ForumLayoutType.LIST_VIEW
            ),
            flags=[name for name, value in channel.flags if value],
        )


class ForumChannel(BaseForumChannel):
    type: ChannelType = pydantic.Field(default=ChannelType.GUILD_FORUM, description="The type of the channel.")

    @classmethod
    def from_discord_channel(cls, channel: DiscordForumChannel) -> ForumChannel:
        """Create a ForumChannel instance from a discord.ForumChannel object."""
        return cls(
            **BaseForumChannel.from_discord_channel(channel).model_dump(),
            type=ChannelType.GUILD_FORUM,
        )


class MediaChannel(BaseForumChannel):
    type: ChannelType = pydantic.Field(default=ChannelType.GUILD_MEDIA, description="The type of the channel.")

    @classmethod
    def from_discord_channel(cls, channel: DiscordForumChannel) -> MediaChannel:
        """Create a MediaChannel instance from a discord.ForumChannel object."""
        return cls(
            **BaseForumChannel.from_discord_channel(channel).model_dump(),
            type=ChannelType.GUILD_MEDIA,
        )


GuildChannel = (
    TextChannel
    | NewsChannel
    | VoiceChannel
    | CategoryChannel
    | StageChannel
    | ThreadChannel
    | ForumChannel
    | MediaChannel
)


class BaseDMChannel(BaseChannel[PrivateChannelT]):
    type: ChannelType = pydantic.Field(default=ChannelType.DM, description="The type of the channel.")
    last_message_id: str | None = pydantic.Field(
        default=None, description="The ID of the last message sent in this channel, if any."
    )

    @classmethod
    def from_discord_channel(cls, channel: PrivateChannelT) -> BaseDMChannel[PrivateChannelT]:
        """Create a BaseDMChannel instance from a discord.abc.PrivateChannel object."""
        return cls(
            **BaseChannel.from_discord_channel(channel).model_dump(),
            type=ChannelType.DM,
            last_message_id=None,
        )


class DMChannel(BaseDMChannel[DiscordDMChannel]):
    recipients: list[PartialUser] = pydantic.Field(
        description="List of users in the DM channel. For a DM, this will contain exactly two users."
    )

    @classmethod
    def from_discord_channel(cls, channel: DiscordDMChannel) -> DMChannel:
        """Create a DMChannel instance from a discord.DMChannel object."""
        return cls(
            **BaseDMChannel.from_discord_channel(channel).model_dump(),
            recipients=[PartialUser.from_discord_user(user) for user in channel.recipients],
        )


class GroupDMChannel(BaseChannel[GroupChannel]):
    type: ChannelType = pydantic.Field(default=ChannelType.GROUP_DM, description="The type of the channel.")
    recipients: list[PartialUser] = pydantic.Field(description="List of users in the group DM channel.")
    owner_id: str = pydantic.Field(description="The ID of the user who created the group DM.")
    icon: str | None = pydantic.Field(default=None, description="The icon hash of the group DM, if any.")

    @classmethod
    def from_discord_channel(cls, channel: GroupChannel) -> GroupDMChannel:
        """Create a GroupDMChannel instance from a discord.GroupChannel object."""
        return cls(
            **BaseDMChannel.from_discord_channel(channel).model_dump(),
            type=ChannelType.GROUP_DM,
            recipients=[PartialUser.from_discord_user(user) for user in channel.recipients],
            owner_id=str(channel.owner.id) if channel.owner else "",
            icon=channel.icon.url if channel.icon else None,
        )


Channel = GuildChannel | DMChannel | GroupDMChannel


class StageInstance(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the stage instance.")
    guild_id: str = pydantic.Field(description="The ID of the guild this stage instance belongs to.")
    channel_id: str = pydantic.Field(description="The ID of the channel this stage instance is in.")
    topic: str = pydantic.Field(description="The topic of the stage instance.")
    privacy_level: int = pydantic.Field(
        description="The privacy level of the stage instance. 1 for public, 2 for guild only."
    )
    discoverable_disabled: bool = pydantic.Field(description="Whether discovery is disabled for the stage instance.")
    guild_scheduled_event_id: str | None = pydantic.Field(
        default=None, description="The ID of the guild scheduled event associated with this stage instance, if any."
    )


class BaseChannelUpdate(pydantic.BaseModel):
    name: str | None = pydantic.Field(default=None, description="The new name of the channel.")
    position: int | None = pydantic.Field(default=None, description="The new position of the channel.")
    permission_overwrites: list[PermissionOverwrite] | None = pydantic.Field(
        default=None, description="The new list of permission overwrites for the channel."
    )
    parent_id: str | None = pydantic.Field(default=None, description="The new ID of the parent category, if any.")


class BaseTextChannelUpdate(BaseChannelUpdate):
    type: t.Literal[ChannelType.GUILD_TEXT, ChannelType.GUILD_ANNOUNCEMENT] | None = pydantic.Field(
        default=None,
        description="The type of the channel. Conversion only supported between text and announcement channels for guilds with the 'NEWS' feature.",
    )
    topic: str | None = pydantic.Field(default=None, description="The new topic of the channel.")
    nsfw: bool | None = pydantic.Field(default=None, description="Whether the channel is NSFW.")
    default_auto_archive_duration: ThreadArchiveDuration | None = pydantic.Field(
        default=None,
        description="The new default auto-archive duration for threads created in this channel. Can be 60, 1440, 4320, or 10080 minutes.",
    )


class TextChannelUpdate(BaseTextChannelUpdate):
    rate_limit_per_user: int | None = pydantic.Field(
        default=None, description="The new rate limit per user in seconds."
    )
    default_thread_rate_limit_per_user: int | None = pydantic.Field(
        default=None, description="The new default rate limit per user for threads created in this channel, if any."
    )


class AnnouncementChannelUpdate(BaseTextChannelUpdate): ...


class BaseForumChannelUpdate(BaseChannelUpdate):
    topic: str | None = pydantic.Field(default=None, description="The new topic of the forum channel.")
    nsfw: bool | None = pydantic.Field(default=None, description="Whether the forum channel is NSFW.")
    rate_limit_per_user: int | None = pydantic.Field(
        default=None, description="The new rate limit per user in seconds."
    )
    default_auto_archive_duration: ThreadArchiveDuration | None = pydantic.Field(
        default=None,
        description="The new default auto-archive duration for threads created in this channel. Can be 60, 1440, 4320, or 10080 minutes.",
    )
    # TODO: Add flags field for edits
    available_tags: list[ForumTag] | None = pydantic.Field(
        default=None, description="The new list of available tags for the forum channel."
    )
    default_reaction_emoji: DefaultReaction | None = pydantic.Field(
        default=None, description="The new default reaction emoji for posts in the forum channel, if any."
    )
    default_thread_rate_limit_per_user: int | None = pydantic.Field(
        default=None, description="The new default rate limit per user for threads created in this channel, if any."
    )
    default_sort_order: ForumOrderType | None = pydantic.Field(
        default=None,
        description="The new default sort order for posts in the forum channel, if any. 0 for latest activity, 1 for creation date.",
    )


class ForumChannelUpdate(BaseForumChannelUpdate):
    default_forum_layout: ForumLayoutType | None = pydantic.Field(
        default=None,
        description="The new default layout for the forum channel, if any. 0 for no default set, 1 for list view, 2 for gallery view.",
    )


class MediaChannelUpdate(BaseForumChannelUpdate): ...


class BaseVoiceChannelUpdate(BaseChannelUpdate):
    nsfw: bool | None = pydantic.Field(default=None, description="Whether the voice channel is NSFW.")
    rate_limit_per_user: int | None = pydantic.Field(
        default=None, description="The new rate limit per user in seconds."
    )
    bitrate: int | None = pydantic.Field(default=None, description="The new bitrate (in bits) of the voice channel.")
    user_limit: int | None = pydantic.Field(default=None, description="The new user limit of the voice channel.")
    rtc_region: str | None = pydantic.Field(
        default=None, description="The new RTC region of the voice channel, if any."
    )
    video_quality_mode: VideoQualityMode | None = pydantic.Field(
        default=None, description="The new video quality mode of the voice channel. 1 for auto, 2 for 720p."
    )


class VoiceChannelUpdate(BaseVoiceChannelUpdate): ...


class StageChannelUpdate(BaseVoiceChannelUpdate): ...


class ThreadChannelUpdate(pydantic.BaseModel):
    name: str | None = pydantic.Field(default=None, description="The new name of the thread.")
    archived: bool | None = pydantic.Field(default=None, description="Whether the thread is archived.")
    auto_archive_duration: ThreadArchiveDuration | None = pydantic.Field(
        default=None,
        description="The new auto-archive duration for the thread. Can be 60, 1440, 4320, or 10080 minutes.",
    )
    locked: bool | None = pydantic.Field(default=None, description="Whether the thread is locked.")
    invitable: bool | None = pydantic.Field(
        default=None, description="Whether non-moderators can add other non-moderators to a private thread."
    )
    rate_limit_per_user: int | None = pydantic.Field(
        default=None, description="The new rate limit per user in seconds."
    )
    # TODO: Add flags field for edits
    applied_tags: list[ForumTag] | None = pydantic.Field(
        default=None, description="The new applied tags for the thread, if any."
    )


ChannelUpdate = (
    TextChannelUpdate
    | AnnouncementChannelUpdate
    | VoiceChannelUpdate
    | StageChannelUpdate
    | ForumChannelUpdate
    | MediaChannelUpdate
    | ThreadChannelUpdate
)


def _discord_channel_to_pydantic(
    channel: discord.abc.GuildChannel | discord.abc.PrivateChannel | discord.Thread,
) -> Channel:
    if isinstance(channel, discord.TextChannel):
        return TextChannel.from_discord_channel(channel)
    elif isinstance(channel, discord.VoiceChannel):
        return VoiceChannel.from_discord_channel(channel)
    elif isinstance(channel, discord.CategoryChannel):
        return CategoryChannel.from_discord_channel(channel)
    elif isinstance(channel, discord.StageChannel):
        return StageChannel.from_discord_channel(channel)
    elif isinstance(channel, discord.Thread):
        return ThreadChannel.from_discord_channel(channel)
    elif isinstance(channel, discord.ForumChannel):
        return ForumChannel.from_discord_channel(channel)
    elif isinstance(channel, discord.DMChannel):
        return DMChannel.from_discord_channel(channel)
    elif isinstance(channel, discord.GroupChannel):
        return GroupDMChannel.from_discord_channel(channel)
    else:
        raise ValueError(f"Unsupported channel type: {type(channel)}")
