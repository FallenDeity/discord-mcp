from __future__ import annotations

import discord
import pydantic

from .member import MemberWithUser

__all__: tuple[str, ...] = (
    "BaseVoiceState",
    "GuildVoiceState",
    "VoiceState",
    "VoiceRegion",
)


class BaseVoiceState(pydantic.BaseModel):
    user_id: str = pydantic.Field(description="The ID of the user.")
    session_id: str = pydantic.Field(description="The session ID of the voice state.")
    deaf: bool = pydantic.Field(description="Whether the user is deafened.")
    mute: bool = pydantic.Field(description="Whether the user is muted.")
    self_deaf: bool = pydantic.Field(description="Whether the user is self-deafened.")
    self_mute: bool = pydantic.Field(description="Whether the user is self-muted.")
    self_video: bool = pydantic.Field(description="Whether the user has their video enabled.")
    suppress: bool = pydantic.Field(description="Whether the user is muted by the server.")
    member: MemberWithUser | None = pydantic.Field(
        default=None, description="The member associated with the voice state, if any."
    )
    self_stream: bool | None = pydantic.Field(
        default=None, description="Whether the user is streaming using 'Go Live', if any."
    )

    @classmethod
    def from_discord_voice_state(cls, user_id: str, state: discord.VoiceState) -> BaseVoiceState:
        """Create a `BaseVoiceState` instance from a `discord.VoiceState` instance."""
        return cls(
            user_id=user_id,
            session_id=state.session_id or "",
            deaf=state.deaf,
            mute=state.mute,
            self_deaf=state.self_deaf,
            self_mute=state.self_mute,
            self_video=state.self_video,
            suppress=state.suppress,
            member=None,
            self_stream=state.self_stream,
        )


class GuildVoiceState(BaseVoiceState):
    channel_id: str = pydantic.Field(description="The ID of the channel the user is connected to.")

    @classmethod
    def from_discord_voice_state(cls, user_id: str, state: discord.VoiceState) -> GuildVoiceState:
        """Create a `GuildVoiceState` instance from a `discord.VoiceState` instance."""
        return cls(
            **BaseVoiceState.from_discord_voice_state(user_id=user_id, state=state).model_dump(),
            channel_id=str(state.channel.id) if state.channel else "",
        )


class VoiceState(BaseVoiceState):
    channel_id: str | None = pydantic.Field(
        default=None, description="The ID of the channel the user is connected to, if any."
    )
    guild_id: str | None = pydantic.Field(
        default=None, description="The ID of the guild the voice state is for, if any."
    )

    @classmethod
    def from_discord_voice_state(cls, user_id: str, state: discord.VoiceState, guild_id: str) -> VoiceState:  # type: ignore[override]
        """Create a `VoiceState` instance from a `discord.VoiceState` instance."""
        return cls(
            **BaseVoiceState.from_discord_voice_state(user_id=user_id, state=state).model_dump(),
            channel_id=str(state.channel.id) if state.channel else None,
            guild_id=guild_id,
        )


class VoiceRegion(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the voice region.")
    name: str = pydantic.Field(description="The name of the voice region.")
    vip: bool = pydantic.Field(description="Whether this is a VIP-only voice region.")
    optimal: bool = pydantic.Field(description="Whether this is the optimal voice region for the current user.")
    deprecated: bool = pydantic.Field(description="Whether this voice region is deprecated.")
    custom: bool = pydantic.Field(description="Whether this is a custom voice region.")
