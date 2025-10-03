from __future__ import annotations

import typing as t

import discord
import pydantic

from .user import User

__all__: tuple[str, ...] = (
    "BaseSoundboardSound",
    "SoundboardSound",
    "SoundboardDefaultSound",
)

SoundboardSoundT = t.TypeVar("SoundboardSoundT", bound=discord.BaseSoundboardSound)


class BaseSoundboardSound(pydantic.BaseModel, t.Generic[SoundboardSoundT]):
    sound_id: str = pydantic.Field(description="The unique ID of the sound.")
    volume: float = pydantic.Field(description="The volume of the sound, between 0.0 and 2.0.")

    @classmethod
    def from_discord_soundboard_sound(cls, sound: SoundboardSoundT) -> BaseSoundboardSound[SoundboardSoundT]:
        return cls(
            sound_id=str(sound.id),
            volume=sound.volume,
        )


class SoundboardSound(BaseSoundboardSound[discord.SoundboardSound]):
    name: str = pydantic.Field(description="The name of the sound.")
    emoji_name: str | None = pydantic.Field(default=None, description="The emoji name of the sound, if any.")
    emoji_id: str | None = pydantic.Field(default=None, description="The emoji ID of the sound, if any.")
    user_id: str | None = pydantic.Field(default=None, description="The ID of the user who uploaded the sound, if any.")
    available: bool = pydantic.Field(description="Whether the sound is available.")
    guild_id: str | None = pydantic.Field(default=None, description="The ID of the guild the sound belongs to, if any.")
    user: User | None = pydantic.Field(default=None, description="The user who uploaded the sound, if any.")

    @classmethod
    def from_discord_soundboard_sound(cls, sound: discord.SoundboardSound) -> SoundboardSound:
        return cls(
            **BaseSoundboardSound.from_discord_soundboard_sound(sound).model_dump(),
            name=sound.name,
            emoji_name=sound.emoji.name if sound.emoji else None,
            emoji_id=str(sound.emoji.id) if sound.emoji and sound.emoji.id else None,
            user_id=str(sound.user.id) if sound.user else None,
            available=sound.available,
            guild_id=str(sound.guild.id) if sound.guild else None,
            user=User.from_discord_user(sound.user) if sound.user else None,
        )


class SoundboardDefaultSound(BaseSoundboardSound[discord.SoundboardDefaultSound]):
    name: str = pydantic.Field(description="The name of the default sound.")
    emoji_name: str | None = pydantic.Field(default=None, description="The emoji name of the default sound, if any.")

    @classmethod
    def from_discord_soundboard_sound(cls, sound: discord.SoundboardDefaultSound) -> SoundboardDefaultSound:
        return cls(
            **BaseSoundboardSound.from_discord_soundboard_sound(sound).model_dump(),
            name=sound.name,
            emoji_name=sound.emoji.name if sound.emoji else None,
        )
