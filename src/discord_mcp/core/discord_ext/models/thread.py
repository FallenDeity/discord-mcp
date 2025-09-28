import typing as t

import pydantic

__all__: tuple[str, ...] = (
    "ThreadMetadata",
    "ThreadMember",
    "ThreadArchiveDuration",
)


ThreadArchiveDuration = t.Literal[60, 1440, 4320, 10080]


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
