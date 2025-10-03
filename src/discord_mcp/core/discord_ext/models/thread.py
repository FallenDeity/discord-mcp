from __future__ import annotations

import enum
import typing as t

import discord
import pydantic

from .common import ForumTag

__all__: tuple[str, ...] = (
    "ThreadMetadata",
    "ThreadMember",
    "ThreadArchiveDuration",
    "ThreadType",
    "Thread",
)


ThreadArchiveDuration = t.Literal[60, 1440, 4320, 10080]


class ThreadType(enum.StrEnum):
    NEWS = "news_thread"
    PUBLIC = "public_thread"
    PRIVATE = "private_thread"


class ThreadMetadata(pydantic.BaseModel):
    archived: bool = pydantic.Field(description="Whether the thread is archived.")
    auto_archive_duration: ThreadArchiveDuration = pydantic.Field(
        description="The duration (in minutes) after which the thread will automatically archive due to inactivity. Can be 60, 1440, 4320, or 10080 minutes."
    )
    archive_timestamp: str = pydantic.Field(
        description="The timestamp when the thread's archive status was last changed."
    )
    locked: bool = pydantic.Field(
        default=False,
        description="Whether the thread is locked. When a thread is locked, only users with 'MANAGE_THREADS' can unarchive it.",
    )
    invitable: bool | None = pydantic.Field(
        default=None,
        description="Whether non-moderators can add other non-moderators to a private thread. Only available on private threads.",
    )
    create_timestamp: str | None = pydantic.Field(
        default=None,
        description="The timestamp when the thread was created. This is only populated for threads created after 2022-01-09.",
    )


class ThreadMember(pydantic.BaseModel):
    id: str | None = pydantic.Field(default=None, description="The ID of the user.")
    user_id: str | None = pydantic.Field(default=None, description="The ID of the user.")
    join_timestamp: str = pydantic.Field(description="The timestamp when the user joined the thread.")
    flags: int = pydantic.Field(description="Any user-thread settings, currently only used for notifications.")

    @classmethod
    def from_discord_thread_member(cls, member: discord.ThreadMember) -> ThreadMember:
        return cls(
            id=str(member.id),
            user_id=str(member.id),
            join_timestamp=member.joined_at.isoformat(),
            flags=member.flags,
        )


class Thread(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the thread.")
    guild_id: str = pydantic.Field(description="The ID of the guild the thread belongs to.")
    parent_id: str | None = pydantic.Field(default=None, description="The ID of the parent channel of the thread.")
    owner_id: str | None = pydantic.Field(default=None, description="The ID of the user who created the thread.")
    name: str = pydantic.Field(description="The name of the thread.")
    type: ThreadType = pydantic.Field(description="The type of the thread.")
    member_count: int | None = pydantic.Field(
        default=None, description="The approximate number of members in the thread, capped at 50."
    )
    message_count: int | None = pydantic.Field(
        default=None, description="The approximate number of messages in the thread."
    )
    total_message_sent: int | None = pydantic.Field(
        default=None, description="The total number of messages sent in the thread."
    )
    rate_limit_per_user: int | None = pydantic.Field(default=None, description="The rate limit per user in seconds.")
    thread_metadata: ThreadMetadata = pydantic.Field(description="The metadata of the thread.")
    member: ThreadMember | None = pydantic.Field(
        default=None, description="The member object for the current user, if they have joined the thread."
    )
    last_message_id: str | None = pydantic.Field(
        default=None, description="The ID of the last message sent in the thread."
    )
    last_pin_timestamp: str | None = pydantic.Field(
        default=None, description="The timestamp of the last pinned message in the thread, if any."
    )
    newly_created: bool | None = pydantic.Field(
        default=None,
        description="Whether the thread was created while the current user was offline. This is only sent when a thread is created and the user has joined the thread.",
    )
    flags: list[str] | None = pydantic.Field(default=None, description="The thread's flags.")
    applied_tags: list[ForumTag] | None = pydantic.Field(
        default=None, description="The details of the tags applied to the thread, if any for forum threads."
    )

    @classmethod
    def from_discord_thread(cls, thread: discord.Thread) -> Thread:
        return cls(
            id=str(thread.id),
            guild_id=str(thread.guild.id),
            parent_id=str(thread.parent.id) if thread.parent else None,
            owner_id=str(thread.owner_id) if thread.owner_id else None,
            name=thread.name,
            type=ThreadType(thread.type.name.lower()),
            member_count=thread.member_count,
            message_count=thread.message_count,
            total_message_sent=thread.total_message_sent,
            rate_limit_per_user=thread.slowmode_delay,
            thread_metadata=ThreadMetadata(
                archived=thread.archived,
                auto_archive_duration=t.cast(t.Literal[60, 1440, 4320, 10080], thread.auto_archive_duration),
                archive_timestamp=thread.archive_timestamp.isoformat(),
                locked=thread.locked,
                invitable=thread.invitable,
                create_timestamp=thread.created_at.isoformat() if thread.created_at else None,
            ),
            member=ThreadMember.from_discord_thread_member(thread.me) if thread.me else None,
            last_message_id=str(thread.last_message_id) if thread.last_message_id else None,
            last_pin_timestamp=None,
            newly_created=None,  # This information is not available in discord.py
            flags=[name for name, value in thread.flags if value],
            applied_tags=(
                [ForumTag.from_discord_forum_tag(tag) for tag in thread.applied_tags] if thread.applied_tags else None
            ),
        )
