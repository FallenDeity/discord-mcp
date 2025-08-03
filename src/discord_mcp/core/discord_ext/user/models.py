from __future__ import annotations

import datetime

import discord
import pydantic

__all__: tuple[str, ...] = ("DiscordUser",)


class DiscordUser(pydantic.BaseModel):
    id: int = pydantic.Field(description="The unique ID of the user.")
    discriminator: str = pydantic.Field(
        description="The user's discriminator, a 4-digit number used to differentiate users with the same username. (deprecated in favor of username)"
    )
    accent_color: tuple[int, int, int] = pydantic.Field(
        description="The user's accent color, represented as an RGB tuple."
    )
    avatar: str = pydantic.Field(description="The URL of the user's avatar.")
    avatar_decoration: str | None = pydantic.Field(
        description="The URL of the user's avatar decoration, if available.", default=None
    )
    avatar_decoration_sku_id: int | None = pydantic.Field(
        description="The SKU ID of the user's avatar decoration, if available.", default=None
    )
    banner: str | None = pydantic.Field(description="The URL of the user's banner, if available.", default=None)
    color: tuple[int, int, int] = pydantic.Field(description="The user's color, represented as an RGB tuple.")
    created_at: datetime.datetime = pydantic.Field(description="The timestamp when the user was created.")
    username: str = pydantic.Field(description="The user's username.")
    bot: bool = pydantic.Field(description="Whether the user is a bot.")
    system: bool = pydantic.Field(description="Whether the user is a system user/official Discord account.")
    public_flags: list[str] = pydantic.Field(
        description="The list of public flags for the user, such as 'Verified', 'Partner', etc."
    )

    @classmethod
    def from_discord_user(cls, user: discord.User | discord.ClientUser) -> DiscordUser:
        """Create a DiscordUser instance from a discord.User object."""
        return cls(
            id=user.id,
            username=user.name,
            discriminator=user.discriminator,
            avatar=user.display_avatar.url,
            avatar_decoration=user.avatar_decoration.url if user.avatar_decoration else None,
            avatar_decoration_sku_id=user.avatar_decoration_sku_id,
            banner=user.banner.url if user.banner else None,
            color=(user.color.r, user.color.g, user.color.b),
            created_at=user.created_at,
            accent_color=(
                (user.accent_color.r, user.accent_color.g, user.accent_color.b) if user.accent_color else (0, 0, 0)
            ),
            bot=user.bot,
            system=user.system,
            public_flags=[f.name for f in user.public_flags.all()],
        )
