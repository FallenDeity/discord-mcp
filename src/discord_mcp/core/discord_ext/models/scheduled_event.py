from __future__ import annotations

import datetime
import enum
import typing as t

import discord
import pydantic

from .user import User

__all__: tuple[str, ...] = (
    "EventStatus",
    "EventEntityType",
    "BaseScheduledEvent",
    "VoiceChannelScheduledEvent",
    "VoiceScheduledEvent",
    "StageInstanceScheduledEvent",
    "EntityMetadata",
    "ExternalScheduledEvent",
    "GuildScheduledEvent",
    "WithUserCount",
    "StageInstanceScheduledEventWithUserCount",
    "VoiceScheduledEventWithUserCount",
    "ExternalScheduledEventWithUserCount",
    "GuildScheduledEventWithUserCount",
    "_discord_scheduled_event_to_pydantic",
)


class EventStatus(enum.StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELED = "canceled"

    @classmethod
    def from_discord_event_status(cls, status: discord.EventStatus) -> EventStatus:
        """Convert a `discord.EventStatus` to an `EventStatus`."""
        return {
            discord.EventStatus.scheduled: cls.SCHEDULED,
            discord.EventStatus.active: cls.ACTIVE,
            discord.EventStatus.completed: cls.COMPLETED,
            discord.EventStatus.canceled: cls.CANCELED,
            discord.EventStatus.ended: cls.COMPLETED,
            discord.EventStatus.cancelled: cls.CANCELED,
        }[status]


class EventEntityType(enum.StrEnum):
    STAGE_INSTANCE = "stage_instance"
    VOICE = "voice"
    EXTERNAL = "external"

    @classmethod
    def from_discord_entity_type(cls, entity_type: discord.EntityType) -> EventEntityType:
        """Convert a `discord.EntityType` to an `EventEntityType`."""
        return {
            discord.EntityType.stage_instance: cls.STAGE_INSTANCE,
            discord.EntityType.voice: cls.VOICE,
            discord.EntityType.external: cls.EXTERNAL,
        }[entity_type]


class BaseScheduledEvent(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the scheduled event.")
    guild_id: str = pydantic.Field(description="The ID of the guild the event belongs to.")
    entity_id: str | None = pydantic.Field(default=None, description="The ID of the entity associated with the event.")
    name: str = pydantic.Field(description="The name of the scheduled event.")
    schedule_start_time: datetime.datetime = pydantic.Field(description="The time the event is scheduled to start.")
    privacy_level: t.Literal[2] = pydantic.Field(description="The privacy level of the scheduled event.")
    status: EventStatus = pydantic.Field(description="The status of the scheduled event.")
    creator_id: str | None = pydantic.Field(
        default=None, description="The ID of the user who created the event, if any."
    )
    description: str | None = pydantic.Field(
        default=None, description="The description of the scheduled event, if any."
    )
    creator: User | None = pydantic.Field(default=None, description="The user who created the event, if any.")
    user_count: int | None = pydantic.Field(
        default=None, description="The number of users subscribed to the event, if any."
    )
    image: str | None = pydantic.Field(default=None, description="The image of the scheduled event, if any.")

    @classmethod
    def from_discord_scheduled_event(cls, event: discord.ScheduledEvent) -> BaseScheduledEvent:
        """Create a `GuildScheduledEvent` instance from a `discord.GuildScheduledEvent` instance."""
        return cls(
            id=str(event.id),
            guild_id=str(event.guild_id),
            entity_id=str(event.entity_id) if event.entity_id else None,
            name=event.name,
            schedule_start_time=event.start_time,
            privacy_level=event.privacy_level.value,
            status=EventStatus.from_discord_event_status(event.status),
            creator_id=str(event.creator_id) if event.creator_id else None,
            description=event.description,
            creator=User.from_discord_user(event.creator) if event.creator else None,
            user_count=event.user_count,
            image=event.cover_image.url if event.cover_image else None,
        )


class VoiceChannelScheduledEvent(BaseScheduledEvent):
    channel_id: str = pydantic.Field(description="The ID of the channel the event is associated with.")
    entity_metadata: t.Literal[None] = pydantic.Field(
        default=None, description="Voice channel events do not have entity metadata."
    )
    scheduled_end_time: datetime.datetime | None = pydantic.Field(
        default=None, description="The time the event is scheduled to end, if any."
    )

    @classmethod
    def from_discord_scheduled_event(cls, event: discord.ScheduledEvent) -> VoiceChannelScheduledEvent:
        """Create a `VoiceChannelScheduledEvent` instance from a `discord.VoiceChannelScheduledEvent` instance."""
        return cls(
            **BaseScheduledEvent.from_discord_scheduled_event(event).model_dump(),
            channel_id=str(event.channel_id),
            entity_metadata=None,
            scheduled_end_time=event.end_time,
        )


class VoiceScheduledEvent(VoiceChannelScheduledEvent):
    entity_type: t.Literal[EventEntityType.VOICE] = pydantic.Field(
        default=EventEntityType.VOICE, description="The type of the scheduled event."
    )

    @classmethod
    def from_discord_scheduled_event(cls, event: discord.ScheduledEvent) -> VoiceScheduledEvent:
        """Create a `VoiceScheduledEvent` instance from a `discord.VoiceScheduledEvent` instance."""
        return cls(
            **VoiceChannelScheduledEvent.from_discord_scheduled_event(event).model_dump(),
            entity_type=EventEntityType.VOICE,
        )


class StageInstanceScheduledEvent(BaseScheduledEvent):
    entity_type: t.Literal[EventEntityType.STAGE_INSTANCE] = pydantic.Field(
        default=EventEntityType.STAGE_INSTANCE, description="The type of the scheduled event."
    )

    @classmethod
    def from_discord_scheduled_event(cls, event: discord.ScheduledEvent) -> StageInstanceScheduledEvent:
        """Create a `StageInstanceScheduledEvent` instance from a `discord.StageInstanceScheduledEvent` instance."""
        return cls(
            **BaseScheduledEvent.from_discord_scheduled_event(event).model_dump(),
            entity_type=EventEntityType.STAGE_INSTANCE,
        )


class EntityMetadata(pydantic.BaseModel):
    location: str = pydantic.Field(description="The location of the external event.")


class ExternalScheduledEvent(BaseScheduledEvent):
    channel_id: t.Literal[None] = pydantic.Field(default=None, description="External events do not have a channel ID.")
    entity_type: t.Literal[EventEntityType.EXTERNAL] = pydantic.Field(
        default=EventEntityType.EXTERNAL, description="The type of the scheduled event."
    )
    entity_metadata: EntityMetadata | None = pydantic.Field(
        default=None, description="The metadata of the external event."
    )
    scheduled_end_time: datetime.datetime | None = pydantic.Field(
        default=None, description="The time the event is scheduled to end, if any."
    )

    @classmethod
    def from_discord_scheduled_event(cls, event: discord.ScheduledEvent) -> ExternalScheduledEvent:
        """Create an `ExternalScheduledEvent` instance from a `discord.ExternalScheduledEvent` instance."""
        return cls(
            **BaseScheduledEvent.from_discord_scheduled_event(event).model_dump(),
            channel_id=None,
            entity_type=EventEntityType.EXTERNAL,
            entity_metadata=EntityMetadata(location=event.location) if event.location else None,
            scheduled_end_time=event.end_time,
        )


GuildScheduledEvent = VoiceScheduledEvent | StageInstanceScheduledEvent | ExternalScheduledEvent


class WithUserCount(pydantic.BaseModel):
    user_count: int = pydantic.Field(description="The number of users subscribed to the event.")

    @classmethod
    def from_discord_scheduled_event(cls, event: discord.ScheduledEvent) -> WithUserCount:
        """Create a `WithUserCount` instance from a `discord.ScheduledEvent` instance."""
        return cls(
            user_count=event.user_count or 0,
        )


class StageInstanceScheduledEventWithUserCount(StageInstanceScheduledEvent, WithUserCount):  # type: ignore[misc]
    @classmethod
    def from_discord_scheduled_event(cls, event: discord.ScheduledEvent) -> StageInstanceScheduledEventWithUserCount:
        """Create a `StageInstanceScheduledEventWithUserCount` instance from a `discord.StageInstanceScheduledEvent` instance."""
        return cls(
            **StageInstanceScheduledEvent.from_discord_scheduled_event(event).model_dump(),
            **WithUserCount.from_discord_scheduled_event(event).model_dump(),
        )


class VoiceScheduledEventWithUserCount(VoiceScheduledEvent, WithUserCount):  # type: ignore[misc]
    @classmethod
    def from_discord_scheduled_event(cls, event: discord.ScheduledEvent) -> VoiceScheduledEventWithUserCount:
        """Create a `VoiceScheduledEventWithUserCount` instance from a `discord.VoiceScheduledEvent` instance."""
        return cls(
            **VoiceScheduledEvent.from_discord_scheduled_event(event).model_dump(),
            **WithUserCount.from_discord_scheduled_event(event).model_dump(),
        )


class ExternalScheduledEventWithUserCount(ExternalScheduledEvent, WithUserCount):  # type: ignore[misc]
    @classmethod
    def from_discord_scheduled_event(cls, event: discord.ScheduledEvent) -> ExternalScheduledEventWithUserCount:
        """Create a `ExternalScheduledEventWithUserCount` instance from a `discord.ExternalScheduledEvent` instance."""
        return cls(
            **ExternalScheduledEvent.from_discord_scheduled_event(event).model_dump(),
            **WithUserCount.from_discord_scheduled_event(event).model_dump(),
        )


GuildScheduledEventWithUserCount = (
    VoiceScheduledEventWithUserCount | StageInstanceScheduledEventWithUserCount | ExternalScheduledEventWithUserCount
)


def _discord_scheduled_event_to_pydantic(event: discord.ScheduledEvent) -> GuildScheduledEvent:
    """Convert a `discord.ScheduledEvent` to the appropriate `GuildScheduledEvent` subclass."""
    if event.entity_type == discord.EntityType.voice:
        return VoiceScheduledEvent.from_discord_scheduled_event(event)
    elif event.entity_type == discord.EntityType.stage_instance:
        return StageInstanceScheduledEvent.from_discord_scheduled_event(event)
    elif event.entity_type == discord.EntityType.external:
        return ExternalScheduledEvent.from_discord_scheduled_event(event)
    else:
        raise ValueError(f"Unknown entity type: {event.entity_type}")
