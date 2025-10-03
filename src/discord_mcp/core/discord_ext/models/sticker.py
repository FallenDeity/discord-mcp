from __future__ import annotations

import enum
import typing as t

import discord
import pydantic

from .user import User

__all__: tuple[str, ...] = (
    "StickerFormatType",
    "StickerType",
    "BaseSticker",
    "StandardSticker",
    "GuildSticker",
    "Sticker",
    "StickerPack",
)

StickerT = t.TypeVar("StickerT", bound=discord.GuildSticker | discord.StandardSticker)


class StickerFormatType(enum.StrEnum):
    PNG = "image/png"
    APNG = "image/apng"
    LOTTIE = "application/json"
    GIF = "image/gif"

    @classmethod
    def from_discord_format_type(cls, format_type: discord.StickerFormatType) -> StickerFormatType:
        return {
            discord.StickerFormatType.png: cls.PNG,
            discord.StickerFormatType.apng: cls.APNG,
            discord.StickerFormatType.lottie: cls.LOTTIE,
            discord.StickerFormatType.gif: cls.GIF,
        }.get(format_type, cls.PNG)


class StickerType(enum.StrEnum):
    STANDARD = "standard"
    GUILD = "guild"


class BaseSticker(pydantic.BaseModel, t.Generic[StickerT]):
    id: str = pydantic.Field(description="The unique ID of the sticker.")
    name: str = pydantic.Field(description="The name of the sticker.")
    description: str | None = pydantic.Field(default=None, description="The description of the sticker.")
    tags: str = pydantic.Field(
        description="A comma-separated list of tags for the sticker used for autocomplete/suggestions."
    )
    format_type: StickerFormatType = pydantic.Field(description="The type of sticker format.")

    @classmethod
    def from_discord_sticker(cls, sticker: StickerT) -> BaseSticker[StickerT]:
        """Create a `BaseSticker` instance from a `discord.Sticker` or `discord.GuildSticker` instance."""
        return cls(
            id=str(sticker.id),
            name=sticker.name,
            description=sticker.description,
            tags=",".join(sticker.tags) if isinstance(sticker, discord.StandardSticker) else sticker.emoji,
            format_type=StickerFormatType.from_discord_format_type(sticker.format),
        )


class StandardSticker(BaseSticker[discord.StandardSticker]):
    type: StickerType = pydantic.Field(default=StickerType.STANDARD, description="The type of sticker.")
    pack_id: str = pydantic.Field(description="The ID of the sticker pack this sticker is from.")
    sort_value: int = pydantic.Field(description="The standard sticker's sort order within its pack.")

    @classmethod
    def from_discord_sticker(cls, sticker: discord.StandardSticker) -> StandardSticker:
        """Create a `StandardSticker` instance from a `discord.Sticker` instance."""
        return cls(
            **BaseSticker.from_discord_sticker(sticker).model_dump(),
            type=StickerType.STANDARD,
            pack_id=str(sticker.pack_id) if sticker.pack_id else "",
            sort_value=sticker.sort_value,
        )


class GuildSticker(BaseSticker[discord.GuildSticker]):
    type: StickerType = pydantic.Field(default=StickerType.GUILD, description="The type of sticker.")
    available: bool | None = pydantic.Field(default=None, description="Whether the guild sticker is available.")
    guild_id: str = pydantic.Field(description="The ID of the guild that owns this sticker.")
    user: User | None = pydantic.Field(default=None, description="The user that uploaded the guild sticker, if any.")

    @classmethod
    def from_discord_sticker(cls, sticker: discord.GuildSticker) -> GuildSticker:
        """Create a `GuildSticker` instance from a `discord.GuildSticker` instance."""
        user = User.from_discord_user(sticker.user) if sticker.user else None
        return cls(
            **BaseSticker.from_discord_sticker(sticker).model_dump(),
            type=StickerType.GUILD,
            available=sticker.available,
            guild_id=str(sticker.guild.id) if sticker.guild else "",
            user=user,
        )


Sticker = StandardSticker | GuildSticker


class StickerPack(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the sticker pack.")
    stickers: list[StandardSticker] = pydantic.Field(
        default_factory=list[StandardSticker], description="The stickers in the pack."
    )
    name: str = pydantic.Field(description="The name of the sticker pack.")
    sku_id: str = pydantic.Field(description="The SKU ID of the sticker pack.")
    cover_sticker_id: str | None = pydantic.Field(
        default=None, description="The ID of a sticker in the pack which is shown as the pack's icon."
    )
    description: str = pydantic.Field(description="The description of the sticker pack.")
    banner_asset_id: str | None = pydantic.Field(default=None, description="The ID of the sticker pack's banner image.")

    @classmethod
    def from_discord_sticker_pack(cls, pack: discord.StickerPack) -> StickerPack:
        """Create a `StickerPack` instance from a `discord.StickerPack` instance."""
        return cls(
            id=str(pack.id),
            stickers=[StandardSticker.from_discord_sticker(sticker) for sticker in pack.stickers],
            name=pack.name,
            sku_id=str(pack.sku_id),
            cover_sticker_id=str(pack.cover_sticker_id) if pack.cover_sticker_id else None,
            description=pack.description,
            banner_asset_id=pack.banner.url if pack.banner else None,
        )
