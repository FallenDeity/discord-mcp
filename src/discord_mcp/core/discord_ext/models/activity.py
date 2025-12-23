from __future__ import annotations

import datetime
import enum
import typing as t

import discord
import pydantic

from .user import User

if t.TYPE_CHECKING:
    from discord.types.activity import ActivityAssets as DiscordActivityAssets
    from discord.types.activity import ActivityParty as DiscordActivityParty
    from discord.types.activity import ActivityTimestamps as DiscordActivityTimestamps

__all__: tuple[str, ...] = (
    "StatusDisplayType",
    "ActivityType",
    "ClientStatus",
    "ActivityTimestamp",
    "ActivityParty",
    "ActivityAssets",
    "ActivitySecrets",
    "ActivityEmoji",
    "SendableActivity",
    "BaseActivity",
    "Activity",
    "PartialPresenceUpdate",
)


ActivityTypes = discord.Activity | discord.CustomActivity | discord.Spotify | discord.Game | discord.Streaming


class StatusType(enum.StrEnum):
    IDLE = "idle"
    DND = "dnd"
    ONLINE = "online"
    OFFLINE = "offline"
    INVISIBLE = "invisible"


class StatusDisplayType(enum.StrEnum):
    NAME = "name"
    STATE = "state"
    DETAILS = "details"


class ActivityType(enum.StrEnum):
    PLAYING = "playing"
    STREAMING = "streaming"
    LISTENING = "listening"
    WATCHING = "watching"
    CUSTOM_STATUS = "custom_status"
    COMPETING = "competing"

    @classmethod
    def from_discord_type(cls, activity_type: discord.ActivityType) -> ActivityType:
        return {
            discord.ActivityType.playing: cls.PLAYING,
            discord.ActivityType.streaming: cls.STREAMING,
            discord.ActivityType.listening: cls.LISTENING,
            discord.ActivityType.watching: cls.WATCHING,
            discord.ActivityType.custom: cls.CUSTOM_STATUS,
            discord.ActivityType.competing: cls.COMPETING,
        }[activity_type]


@discord.flags.fill_with_flags()
class ActivityFlags(discord.flags.BaseFlags):
    __slots__ = ()

    @discord.flags.flag_value
    def instance(self) -> int:
        """This activity is an instanced game session."""
        return 1

    @discord.flags.flag_value
    def join(self) -> int:
        """This activity has a join button."""
        return 2

    @discord.flags.flag_value
    def spectate(self) -> int:
        """This activity has a spectate button."""
        return 4

    @discord.flags.flag_value
    def join_request(self) -> int:
        """This activity has a join request button."""
        return 8

    @discord.flags.flag_value
    def sync(self) -> int:
        """This activity is synced from a third party."""
        return 16

    @discord.flags.flag_value
    def play(self) -> int:
        """This activity is a play activity."""
        return 32


class ClientStatus(pydantic.BaseModel):
    desktop: str | None = pydantic.Field(default=None, description="The user's status on desktop.")
    mobile: str | None = pydantic.Field(default=None, description="The user's status on mobile.")
    web: str | None = pydantic.Field(default=None, description="The user's status on web.")


class ActivityTimestamp(pydantic.BaseModel):
    start: datetime.datetime | None = pydantic.Field(
        default=None, description="The timestamp when the activity started, if any."
    )
    end: datetime.datetime | None = pydantic.Field(
        default=None, description="The timestamp when the activity ended, if any."
    )

    @classmethod
    def from_discord_timestamps(cls, timestamps: DiscordActivityTimestamps | None) -> ActivityTimestamp:
        """Create an `ActivityTimestamp` instance from a `discord.ActivityTimestamps` instance."""
        start = timestamps["start"] if timestamps and "start" in timestamps else None
        end = timestamps["end"] if timestamps and "end" in timestamps else None
        return cls(
            start=datetime.datetime.fromtimestamp(start / 1000, tz=datetime.timezone.utc) if start else None,
            end=datetime.datetime.fromtimestamp(end / 1000, tz=datetime.timezone.utc) if end else None,
        )


class ActivityParty(pydantic.BaseModel):
    id: str | None = pydantic.Field(default=None, description="The ID of the party.")
    size: list[int] | None = pydantic.Field(
        default=None, description="A list of two integers representing the current and maximum size of the party."
    )

    @classmethod
    def from_discord_party(cls, party: DiscordActivityParty | None) -> ActivityParty:
        """Create an `ActivityParty` instance from a `discord.ActivityParty` instance."""
        return cls(id=party.get("id"), size=party.get("size")) if party else cls()


class ActivityAssets(pydantic.BaseModel):
    large_image: str | None = pydantic.Field(default=None, description="The ID of the large image asset.")
    large_text: str | None = pydantic.Field(
        default=None, description="The text displayed when hovering over the large image."
    )
    small_image: str | None = pydantic.Field(default=None, description="The ID of the small image asset.")
    small_text: str | None = pydantic.Field(
        default=None, description="The text displayed when hovering over the small image."
    )
    large_url: str | None = pydantic.Field(default=None, description="The URL of the large image asset, if it's a URL.")
    small_url: str | None = pydantic.Field(default=None, description="The URL of the small image asset, if it's a URL.")

    @classmethod
    def from_discord_assets(cls, assets: DiscordActivityAssets | None) -> ActivityAssets:
        """Create an `ActivityAssets` instance from a `discord.ActivityAssets` instance."""
        return (
            cls(
                large_image=assets.get("large_image"),
                large_text=assets.get("large_text"),
                small_image=assets.get("small_image"),
                small_text=assets.get("small_text"),
                large_url=assets.get("large_url"),
                small_url=assets.get("small_url"),
            )
            if assets
            else cls()
        )


class ActivitySecrets(pydantic.BaseModel):
    join: str | None = pydantic.Field(default=None, description="The secret for joining a party.")
    spectate: str | None = pydantic.Field(default=None, description="The secret for spectating a game.")
    match: str | None = pydantic.Field(default=None, description="The secret for a specific instanced match.")


class ActivityEmoji(pydantic.BaseModel):
    name: str = pydantic.Field(description="The name of the emoji.")
    id: str | None = pydantic.Field(default=None, description="The ID of the emoji, if it's a custom emoji.")
    animated: bool | None = pydantic.Field(
        default=None, description="Whether the emoji is animated, if it's a custom emoji."
    )

    @classmethod
    def from_discord_emoji(cls, emoji: discord.Emoji | discord.PartialEmoji | None) -> ActivityEmoji | None:
        """Create an `ActivityEmoji` instance from a `discord.Emoji` or `discord.PartialEmoji` instance."""
        return (
            cls(
                name=emoji.name,
                id=str(emoji.id) if isinstance(emoji, discord.Emoji) else None,
                animated=emoji.animated if isinstance(emoji, discord.Emoji) else None,
            )
            if emoji
            else None
        )


class SendableActivity(pydantic.BaseModel):
    name: str = pydantic.Field(description="The name of the activity.")
    type: ActivityType = pydantic.Field(description="The type of activity.")
    url: str | None = pydantic.Field(default=None, description="The URL of the activity, if applicable.")

    @classmethod
    def from_discord_activity(cls, activity: ActivityTypes) -> SendableActivity:
        """Create a `SendableActivity` instance from a `discord.Activity` instance."""
        return cls(
            name=activity.name if activity.name else "Custom Status",
            type=ActivityType.from_discord_type(activity.type),
            url=activity.url if isinstance(activity, discord.Streaming) else None,
        )


class BaseActivity(SendableActivity):
    created_at: datetime.datetime = pydantic.Field(description="The timestamp when the activity was created.")

    @classmethod
    def from_discord_activity(cls, activity: ActivityTypes) -> BaseActivity:
        """Create a `BaseActivity` instance from a `discord.Activity` instance."""
        return cls(
            **SendableActivity.from_discord_activity(activity).model_dump(),
            created_at=activity.created_at or datetime.datetime.now(),
        )


class Activity(BaseActivity):
    state: str | None = pydantic.Field(default=None, description="The user's current state.")
    details: str | None = pydantic.Field(default=None, description="The user's current details.")
    timestamps: ActivityTimestamp | None = pydantic.Field(
        default=None, description="The timestamps for the activity, if any."
    )
    platform: str | None = pydantic.Field(default=None, description="The platform the user is on, if any.")
    assets: ActivityAssets | None = pydantic.Field(default=None, description="The assets for the activity, if any.")
    party: ActivityParty | None = pydantic.Field(
        default=None, description="The party information for the activity, if any."
    )
    application_id: str | None = pydantic.Field(
        default=None, description="The application ID for the activity, if any."
    )
    flags: list[str] | None = pydantic.Field(default=None, description="The flags for the activity, if any.")
    emoji: ActivityEmoji | None = pydantic.Field(
        default=None, description="The emoji for custom status activities, if any."
    )
    secrets: ActivitySecrets | None = pydantic.Field(default=None, description="The secrets for the activity, if any.")
    session_id: str | None = pydantic.Field(default=None, description="The session ID for the activity, if any.")
    instance: bool | None = pydantic.Field(
        default=None, description="Whether the activity is an instanced game session, if any."
    )
    buttons: list[str] | None = pydantic.Field(default=None, description="The custom buttons for the activity, if any.")
    sync_id: str | None = pydantic.Field(
        default=None, description="The ID of the Spotify track, if the activity is Spotify."
    )
    state_url: str | None = pydantic.Field(default=None, description="The URL of the activity's state, if any.")
    details_url: str | None = pydantic.Field(default=None, description="The URL of the activity's details, if any.")
    status_display_type: StatusDisplayType | None = pydantic.Field(
        default=None, description="The display type for the activity's status, if any."
    )

    @classmethod
    def from_discord_activity(cls, activity: ActivityTypes) -> Activity:
        base = cls(**BaseActivity.from_discord_activity(activity).model_dump())

        handlers: dict[type[ActivityTypes], t.Callable[[Activity, t.Any], None]] = {
            discord.Activity: cls._from_generic,
            discord.Streaming: cls._from_streaming,
            discord.Spotify: cls._from_spotify,
            discord.Game: cls._from_game,
            discord.CustomActivity: cls._from_custom,
        }

        for activity_type, handler in handlers.items():
            if isinstance(activity, activity_type):
                handler(base, activity)
                break

        return base

    @staticmethod
    def _from_generic(obj: "Activity", act: discord.Activity):
        obj.state = act.state
        obj.details = act.details
        obj.timestamps = ActivityTimestamp.from_discord_timestamps(act.timestamps)
        obj.platform = act.platform
        obj.assets = ActivityAssets.from_discord_assets(act.assets)
        obj.party = ActivityParty.from_discord_party(act.party)
        obj.application_id = str(act.application_id) if act.application_id else None
        obj.flags = [name for name, value in ActivityFlags._from_value(act.flags) if value]
        obj.emoji = ActivityEmoji.from_discord_emoji(act.emoji)
        obj.session_id = act.session_id
        obj.buttons = act.buttons
        obj.sync_id = act.sync_id
        obj.state_url = act.state_url
        obj.details_url = act.details_url
        obj.status_display_type = StatusDisplayType(act.status_display_type) if act.status_display_type else None

    @staticmethod
    def _from_streaming(obj: "Activity", act: discord.Streaming):
        obj.state = act.game
        obj.details = act.details
        obj.platform = act.platform
        obj.assets = ActivityAssets.from_discord_assets(act.assets)

    @staticmethod
    def _from_spotify(obj: "Activity", act: discord.Spotify):
        obj.state = act.artist
        obj.details = act.title
        obj.timestamps = ActivityTimestamp(start=act.start, end=act.end)
        obj.platform = "Spotify"
        obj.assets = ActivityAssets.from_discord_assets(act._assets)
        obj.party = ActivityParty.from_discord_party(act._party)
        obj.flags = ["sync", "play"]
        obj.session_id = act._session_id
        obj.sync_id = act._sync_id

    @staticmethod
    def _from_game(obj: "Activity", act: discord.Game):
        obj.timestamps = ActivityTimestamp(start=act.start, end=act.end)
        obj.platform = act.platform
        obj.assets = ActivityAssets.from_discord_assets(act.assets)

    @staticmethod
    def _from_custom(obj: "Activity", act: discord.CustomActivity):
        obj.state = act.state
        obj.emoji = ActivityEmoji.from_discord_emoji(act.emoji)


class PartialPresenceUpdate(pydantic.BaseModel):
    user: User = pydantic.Field(description="The user whose presence is being updated.")
    guild_id: str = pydantic.Field(description="The ID of the guild where the presence update is occurring.")
    status: StatusType = pydantic.Field(description="The status type of the user.")
    activities: list[Activity] = pydantic.Field(
        default_factory=list[Activity], description="A list of the user's current activities."
    )
    client_status: ClientStatus | None = pydantic.Field(
        default=None, description="The user's status on different platforms, if any."
    )

    @classmethod
    def from_discord_presence(cls, member: discord.Member) -> PartialPresenceUpdate:
        """Create a `PartialPresenceUpdate` instance from a `discord.Member` instance."""
        return cls(
            user=User.from_discord_user(member),
            guild_id=str(member.guild.id),
            status=StatusType(member.status.value),
            activities=[Activity.from_discord_activity(activity) for activity in member.activities],
            client_status=ClientStatus(
                desktop=member.desktop_status.value,
                mobile=member.mobile_status.value,
                web=member.web_status.value,
            ),
        )
