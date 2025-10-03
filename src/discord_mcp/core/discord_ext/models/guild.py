from __future__ import annotations

import datetime
import enum
import typing as t

import discord
import pydantic

from .activity import PartialPresenceUpdate
from .channel import GuildChannel, StageInstance, _discord_channel_to_pydantic
from .emoji import Emoji
from .member import Member
from .role import Role
from .scheduled_event import GuildScheduledEvent, _discord_scheduled_event_to_pydantic
from .soundboard import SoundboardSound
from .sticker import GuildSticker
from .thread import Thread
from .voice import GuildVoiceState
from .welcome_screen import WelcomeScreen

GuildT = t.TypeVar("GuildT", bound=discord.Guild | discord.PartialInviteGuild)

GuildFeature = t.Literal[
    "ANIMATED_BANNER",
    "ANIMATED_ICON",
    "APPLICATION_COMMAND_PERMISSIONS_V2",
    "AUTO_MODERATION",
    "BANNER",
    "COMMUNITY",
    "CREATOR_MONETIZABLE_PROVISIONAL",
    "CREATOR_STORE_PAGE",
    "DEVELOPER_SUPPORT_SERVER",
    "DISCOVERABLE",
    "FEATURABLE",
    "INVITE_SPLASH",
    "INVITES_DISABLED",
    "MEMBER_VERIFICATION_GATE_ENABLED",
    "MONETIZATION_ENABLED",
    "MORE_EMOJI",
    "MORE_STICKERS",
    "NEWS",
    "PARTNERED",
    "PREVIEW_ENABLED",
    "ROLE_ICONS",
    "ROLE_SUBSCRIPTIONS_AVAILABLE_FOR_PURCHASE",
    "ROLE_SUBSCRIPTIONS_ENABLED",
    "TICKETED_EVENTS_ENABLED",
    "VANITY_URL",
    "VERIFIED",
    "VIP_REGIONS",
    "WELCOME_SCREEN_ENABLED",
    "ENHANCED_ROLE_COLORS",
    "RAID_ALERTS_DISABLED",
    "SOUNDBOARD",
    "MORE_SOUNDBOARD",
    "GUESTS_ENABLED",
    "GUILD_TAGS",
    # NOTE: not in discord documentation but present in the API responses
    "NEW_THREAD_PERMISSIONS",
    "ACTIVITY_FEED_DISABLED_BY_USER",
    "CREATOR_ACCEPTED_NEW_TERMS",
    "CHANNEL_ICON_EMOJIS_GENERATED",
    "GUILD_ONBOARDING_EVER_ENABLED",
    "GUILD_ONBOARDING",
    "GUILD_ONBOARDING_HAS_PROMPTS",
    "PRIVATE_THREADS",
    "THREE_DAY_THREAD_ARCHIVE",
    "GUILD_SERVER_GUIDE",
    "THREADS_ENABLED",
    "MEMBER_PROFILES",
    "COMMUNITY_EXP_MEDIUM",
    "SEVEN_DAY_THREAD_ARCHIVE",
    "TEXT_IN_VOICE_ENABLED",
    "EXPOSED_TO_ACTIVITIES_WTP_EXPERIMENT",
    "ENABLED_MODERATION_EXPERIENCE_FOR_NON_COMMUNITY",
    "ENABLED_DISCOVERABLE_BEFORE",
    "GUILD_WEB_PAGE_VANITY_URL",
]


class Locale(enum.StrEnum):
    american_english = "en-US"
    british_english = "en-GB"
    bulgarian = "bg"
    chinese = "zh-CN"
    taiwan_chinese = "zh-TW"
    croatian = "hr"
    czech = "cs"
    indonesian = "id"
    danish = "da"
    dutch = "nl"
    finnish = "fi"
    french = "fr"
    german = "de"
    greek = "el"
    hindi = "hi"
    hungarian = "hu"
    italian = "it"
    japanese = "ja"
    korean = "ko"
    latin_american_spanish = "es-419"
    lithuanian = "lt"
    norwegian = "no"
    polish = "pl"
    brazil_portuguese = "pt-BR"
    romanian = "ro"
    russian = "ru"
    spain_spanish = "es-ES"
    swedish = "sv-SE"
    thai = "th"
    turkish = "tr"
    ukrainian = "uk"
    vietnamese = "vi"


class VerificationLevel(enum.StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

    @classmethod
    def from_discord_verification_level(cls, level: discord.VerificationLevel) -> VerificationLevel:
        """Convert a `discord.VerificationLevel` to a `VerificationLevel`."""
        return {
            discord.VerificationLevel.none: cls.NONE,
            discord.VerificationLevel.low: cls.LOW,
            discord.VerificationLevel.medium: cls.MEDIUM,
            discord.VerificationLevel.high: cls.HIGH,
            discord.VerificationLevel.highest: cls.VERY_HIGH,
        }[level]


class DefaultMessageNotificationLevel(enum.StrEnum):
    UNKNOWN = "unknown"
    ALL_MESSAGES = "all_messages"
    ONLY_MENTIONS = "only_mentions"

    @classmethod
    def from_discord_notification_level(cls, level: discord.NotificationLevel) -> DefaultMessageNotificationLevel:
        """Convert a `discord.NotificationLevel` to a `DefaultMessageNotificationLevel`."""
        return {
            discord.NotificationLevel.all_messages: cls.ALL_MESSAGES,
            discord.NotificationLevel.only_mentions: cls.ONLY_MENTIONS,
        }.get(level, cls.UNKNOWN)


class ExplicitContentFilterLevel(enum.StrEnum):
    UNKNOWN = "unknown"
    DISABLED = "disabled"
    MEMBERS_WITHOUT_ROLES = "members_without_roles"
    ALL_MEMBERS = "all_members"

    @classmethod
    def from_discord_explicit_content_filter_level(cls, level: discord.ContentFilter) -> ExplicitContentFilterLevel:
        """Convert a `discord.ContentFilter` to an `ExplicitContentFilterLevel`."""
        return {
            discord.ContentFilter.disabled: cls.DISABLED,
            discord.ContentFilter.no_role: cls.MEMBERS_WITHOUT_ROLES,
            discord.ContentFilter.all_members: cls.ALL_MEMBERS,
        }.get(level, cls.UNKNOWN)


class MFALevel(enum.StrEnum):
    UNKNOWN = "unknown"
    NONE = "none"
    ELEVATED = "elevated"

    @classmethod
    def from_discord_mfa_level(cls, level: discord.MFALevel) -> MFALevel:
        """Convert a `discord.MFALevel` to an `MFALevel`."""
        return {
            discord.MFALevel.disabled: cls.NONE,
            discord.MFALevel.require_2fa: cls.ELEVATED,
        }.get(level, cls.UNKNOWN)


class GuildNSFWLevel(enum.StrEnum):
    DEFAULT = "default"
    EXPLICIT = "explicit"
    SAFE = "safe"
    AGE_RESTRICTED = "age_restricted"

    @classmethod
    def from_discord_nsfw_level(cls, level: discord.NSFWLevel) -> GuildNSFWLevel:
        """Convert a `discord.NSFWLevel` to a `GuildNSFWLevel`."""
        return {
            discord.NSFWLevel.default: cls.DEFAULT,
            discord.NSFWLevel.explicit: cls.EXPLICIT,
            discord.NSFWLevel.safe: cls.SAFE,
            discord.NSFWLevel.age_restricted: cls.AGE_RESTRICTED,
        }[level]


class PremiumTier(enum.StrEnum):
    UNKNOWN = "unknown"
    NONE = "none"
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"

    @classmethod
    def from_discord_premium_tier(cls, tier: int | t.Literal[0, 1, 2, 3]) -> PremiumTier:
        """Convert a `discord.PremiumTier` to a `PremiumTier`."""
        return {
            0: cls.NONE,
            1: cls.TIER_1,
            2: cls.TIER_2,
            3: cls.TIER_3,
        }.get(tier, cls.UNKNOWN)


class IncidentData(pydantic.BaseModel):
    invites_disabled_until: datetime.datetime | None = pydantic.Field(
        default=None, description="The time until which invites are disabled due to an incident."
    )
    dms_disabled_until: datetime.datetime | None = pydantic.Field(
        default=None, description="The time until which direct messages are disabled due to an incident."
    )
    dm_spam_detected_at: datetime.datetime | None = pydantic.Field(
        default=None, description="The time at which direct message spam was detected."
    )
    raid_detected_at: datetime.datetime | None = pydantic.Field(
        default=None, description="The time at which a raid was detected."
    )

    @classmethod
    def from_discord_incident_data(cls, data: discord.Guild) -> IncidentData:
        """Create an `IncidentData` instance from a `discord.Guild` instance."""
        return cls(
            invites_disabled_until=data.invites_paused_until,
            dms_disabled_until=data.dms_paused_until,
            dm_spam_detected_at=data.dm_spam_detected_at,
            raid_detected_at=data.raid_detected_at,
        )


class UnavailableGuild(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the guild.")
    unavailable: bool = pydantic.Field(
        description="Indicates whether its a partial guild, whose information hasn't been provided through the GUILD_CREATE event."
    )

    @classmethod
    def from_discord_guild(cls, guild: discord.Guild) -> UnavailableGuild:
        """Create an `UnavailableGuild` instance from a `discord.Guild` instance."""
        return cls(
            id=str(guild.id),
            unavailable=guild.unavailable,
        )


class BaseGuildPreview(UnavailableGuild):
    name: str = pydantic.Field(description="The name of the guild.")
    icon: str | None = pydantic.Field(default=None, description="The icon hash of the guild.")
    splash: str | None = pydantic.Field(default=None, description="The splash hash of the guild.")
    discovery_splash: str | None = pydantic.Field(default=None, description="The discovery splash hash of the guild.")
    emojis: list[Emoji] = pydantic.Field(default_factory=list[Emoji], description="The custom emojis of the guild.")
    stickers: list[GuildSticker] = pydantic.Field(
        default_factory=list[GuildSticker], description="The custom stickers of the guild."
    )
    features: list[GuildFeature] = pydantic.Field(
        default_factory=list[GuildFeature], description="The enabled guild features."
    )
    description: str | None = pydantic.Field(default=None, description="The description of the guild.")
    incidents_data: IncidentData | None = pydantic.Field(
        default=None, description="The incident data of the guild, if any."
    )

    @classmethod
    def from_discord_guild(cls, guild: discord.Guild) -> BaseGuildPreview:
        """Create a `BaseGuildPreview` instance from a `discord.Guild` instance."""
        return cls(
            **UnavailableGuild.from_discord_guild(guild).model_dump(),
            name=guild.name,
            icon=guild.icon.url if guild.icon else None,
            splash=guild.splash.url if guild.splash else None,
            discovery_splash=guild.discovery_splash.url if guild.discovery_splash else None,
            emojis=[Emoji.from_discord_emoji(emoji) for emoji in guild.emojis],
            stickers=[GuildSticker.from_discord_sticker(sticker) for sticker in guild.stickers],
            features=t.cast(list[GuildFeature], guild.features),
            description=guild.description,
            incidents_data=IncidentData.from_discord_incident_data(guild) if guild._incidents_data else None,
        )


class GuildPreviewWithCounts(pydantic.BaseModel, t.Generic[GuildT]):
    approximate_member_count: int = pydantic.Field(description="Approximate number of members in this guild.")
    approximate_presence_count: int = pydantic.Field(
        description="Approximate number of non-offline members in this guild."
    )

    @classmethod
    def from_discord_guild(cls, guild: GuildT) -> GuildPreviewWithCounts[GuildT]:
        """Create a `GuildPreviewWithCounts` instance from a `discord.Guild` instance."""
        approx_member_count, approx_presence_count = 0, 0
        if isinstance(guild, discord.Guild):
            approx_member_count = guild.approximate_member_count or 0
            approx_presence_count = guild.approximate_presence_count or 0
        return cls(
            approximate_member_count=approx_member_count,
            approximate_presence_count=approx_presence_count,
        )


class GuildPreview(BaseGuildPreview, GuildPreviewWithCounts[discord.Guild]):
    @classmethod
    def from_discord_guild(cls, guild: discord.Guild) -> GuildPreview:
        """Create a `GuildPreview` instance from a `discord.Guild` instance."""
        return cls(
            **BaseGuildPreview.from_discord_guild(guild).model_dump(),
            **GuildPreviewWithCounts.from_discord_guild(guild).model_dump(),
        )


class Guild(BaseGuildPreview):
    owner_id: str = pydantic.Field(description="The ID of the guild owner.")
    region: str | None = pydantic.Field(default=None, description="The voice region ID for the guild. (deprecated)")
    afk_channel_id: str | None = pydantic.Field(default=None, description="The ID of the AFK channel.")
    afk_timeout: int = pydantic.Field(description="The AFK timeout in seconds.")
    verification_level: VerificationLevel = pydantic.Field(description="The verification level required for the guild.")
    default_message_notifications: DefaultMessageNotificationLevel = pydantic.Field(
        description="The default message notification level."
    )
    explicit_content_filter: ExplicitContentFilterLevel = pydantic.Field(
        description="The explicit content filter level."
    )
    roles: list[Role] = pydantic.Field(default_factory=list[Role], description="The roles in the guild.")
    mfa_level: MFALevel = pydantic.Field(description="The required MFA level for the guild.")
    nsfw_level: GuildNSFWLevel = pydantic.Field(description="The guild's NSFW level.")
    application_id: str | None = pydantic.Field(
        default=None, description="The application ID of the guild creator if it is bot-created."
    )
    system_channel_id: str | None = pydantic.Field(default=None, description="The ID of the system channel.")
    system_channel_flags: list[str] = pydantic.Field(description="The system channel flags.")
    rules_channel_id: str | None = pydantic.Field(default=None, description="The ID of the rules channel.")
    vanity_url_code: str | None = pydantic.Field(default=None, description="The vanity URL code for the guild.")
    banner: str | None = pydantic.Field(default=None, description="The banner hash of the guild.")
    premium_tier: PremiumTier = pydantic.Field(description="The premium tier (Server Boost level) of the guild.")
    preferred_locale: Locale = pydantic.Field(description="The preferred locale of the guild.")
    public_updates_channel_id: str | None = pydantic.Field(
        default=None, description="The ID of the channel where admins and moderators receive notices from Discord."
    )
    stage_instances: list[StageInstance] = pydantic.Field(
        default_factory=list[StageInstance], description="The stage instances in the guild."
    )
    guild_scheduled_events: list[GuildScheduledEvent] = pydantic.Field(
        default_factory=list[GuildScheduledEvent], description="The scheduled events in the guild."
    )
    icon_hash: str | None = pydantic.Field(default=None, description="The icon hash of the guild.")
    owner: bool | None = pydantic.Field(default=None, description="Whether the current user is the owner of the guild.")
    permissions: str | None = pydantic.Field(
        default=None, description="The permissions of the current user in the guild, if available."
    )
    widget_enabled: bool | None = pydantic.Field(default=None, description="Whether the guild widget is enabled.")
    widget_channel_id: str | None = pydantic.Field(
        default=None, description="The channel ID that the widget will generate an invite to, if enabled."
    )
    joined_at: datetime.datetime | None = pydantic.Field(
        default=None, description="The time at which the current user joined the guild."
    )
    large: bool | None = pydantic.Field(default=None, description="Whether this guild is considered large.")
    member_count: int | None = pydantic.Field(default=None, description="The total number of members in the guild.")
    voice_states: list[GuildVoiceState] = pydantic.Field(
        default_factory=list[GuildVoiceState], description="The voice states of members in the guild."
    )
    members: list[Member] = pydantic.Field(default_factory=list[Member], description="The members in the guild.")
    channels: list[GuildChannel] = pydantic.Field(
        default_factory=list[GuildChannel], description="The channels in the guild."
    )
    presences: list[PartialPresenceUpdate] = pydantic.Field(
        default_factory=list[PartialPresenceUpdate], description="The presences of members in the guild."
    )
    threads: list[Thread] = pydantic.Field(default_factory=list[Thread], description="The threads in the guild.")
    max_presences: int | None = pydantic.Field(
        default=None, description="The maximum number of presences for the guild."
    )
    max_members: int | None = pydantic.Field(default=None, description="The maximum number of members for the guild.")
    premium_subscription_count: int | None = pydantic.Field(
        default=None, description="The number of boosts this guild currently has."
    )
    max_video_channel_users: int | None = pydantic.Field(
        default=None, description="The maximum amount of users in a video channel."
    )
    soundboard_sounds: list[SoundboardSound] = pydantic.Field(
        default_factory=list[SoundboardSound], description="The custom soundboard sounds in the guild."
    )

    @classmethod
    def from_discord_guild(cls, guild: discord.Guild) -> Guild:
        """Create a `Guild` instance from a `discord.Guild` instance."""
        return cls(
            **BaseGuildPreview.from_discord_guild(guild).model_dump(),
            owner_id=str(guild.owner_id) if guild.owner_id else "",
            # TODO: dpy dosent provide this from the guild object
            region=None,
            afk_channel_id=str(guild.afk_channel.id) if guild.afk_channel else None,
            afk_timeout=guild.afk_timeout,
            verification_level=VerificationLevel.from_discord_verification_level(guild.verification_level),
            default_message_notifications=DefaultMessageNotificationLevel.from_discord_notification_level(
                guild.default_notifications
            ),
            explicit_content_filter=ExplicitContentFilterLevel.from_discord_explicit_content_filter_level(
                guild.explicit_content_filter
            ),
            roles=[Role.from_discord_role(role) for role in guild.roles],
            mfa_level=MFALevel.from_discord_mfa_level(guild.mfa_level),
            nsfw_level=GuildNSFWLevel.from_discord_nsfw_level(guild.nsfw_level),
            # TODO: dpy doesnt provide this from the guild object
            application_id=None,
            system_channel_id=str(guild.system_channel.id) if guild.system_channel else None,
            system_channel_flags=[name for name, value in guild.system_channel_flags if value],
            rules_channel_id=str(guild.rules_channel.id) if guild.rules_channel else None,
            vanity_url_code=guild.vanity_url_code,
            banner=guild.banner.url if guild.banner else None,
            premium_tier=PremiumTier.from_discord_premium_tier(guild.premium_tier),
            preferred_locale=Locale(guild.preferred_locale.value),
            public_updates_channel_id=str(guild.public_updates_channel.id) if guild.public_updates_channel else None,
            stage_instances=[StageInstance.from_discord_stage_instance(si) for si in guild.stage_instances],
            guild_scheduled_events=[_discord_scheduled_event_to_pydantic(se) for se in guild.scheduled_events],
            icon_hash=guild.icon.url if guild.icon else None,
            owner=None,
            permissions=None,
            widget_enabled=guild.widget_enabled,
            widget_channel_id=str(guild.widget_channel.id) if guild.widget_channel else None,
            joined_at=guild.me.joined_at if guild.me else None,
            large=guild.large,
            member_count=guild.member_count,
            voice_states=[
                GuildVoiceState.from_discord_voice_state(str(uid), vs) for uid, vs in guild._voice_states.items()
            ],
            members=[Member.from_discord_member(member) for member in guild.members],
            channels=[t.cast(GuildChannel, _discord_channel_to_pydantic(channel)) for channel in guild.channels],
            presences=[PartialPresenceUpdate.from_discord_presence(m) for m in guild.members],
            threads=[Thread.from_discord_thread(thread) for thread in guild.threads],
            max_presences=guild.max_presences,
            max_members=guild.max_members,
            premium_subscription_count=guild.premium_subscription_count,
            max_video_channel_users=guild.max_video_channel_users,
            soundboard_sounds=[
                SoundboardSound.from_discord_soundboard_sound(sound) for sound in guild.soundboard_sounds
            ],
        )


class InviteGuild(Guild):
    welcome_screen: WelcomeScreen | None = pydantic.Field(
        default=None, description="The welcome screen of the guild, if set."
    )

    @classmethod
    def from_discord_guild(cls, guild: discord.Guild | discord.PartialInviteGuild) -> InviteGuild:
        """Create an `InviteGuild` instance from a `discord.Guild` instance."""
        if isinstance(guild, discord.Guild):
            return cls(
                **Guild.from_discord_guild(guild).model_dump(),
                # TODO: Check if dpy is extracting this from returned payload without an extra api call
                welcome_screen=None,
            )
        return cls(
            id=str(guild.id),
            name=guild.name,
            unavailable=False,
            owner_id="",
            afk_timeout=0,
            verification_level=VerificationLevel.from_discord_verification_level(guild.verification_level),
            default_message_notifications=DefaultMessageNotificationLevel.UNKNOWN,
            explicit_content_filter=ExplicitContentFilterLevel.UNKNOWN,
            mfa_level=MFALevel.UNKNOWN,
            nsfw_level=GuildNSFWLevel.from_discord_nsfw_level(guild.nsfw_level),
            system_channel_flags=[],
            premium_tier=PremiumTier.UNKNOWN,
            preferred_locale=Locale.american_english,
            banner=guild.banner.url if guild.banner else None,
            description=guild.description,
            features=t.cast(list[GuildFeature], guild.features),
            icon=guild.icon.url if guild.icon else None,
            premium_subscription_count=guild.premium_subscription_count,
            splash=guild.splash.url if guild.splash else None,
            vanity_url_code=guild.vanity_url_code,
        )


class GuildWithCounts(Guild, GuildPreviewWithCounts[discord.Guild]):
    @classmethod
    def from_discord_guild(cls, guild: discord.Guild) -> GuildWithCounts:
        """Create a `GuildWithCounts` instance from a `discord.Guild` instance."""
        return cls(
            **Guild.from_discord_guild(guild).model_dump(),
            **GuildPreviewWithCounts.from_discord_guild(guild).model_dump(),
        )
