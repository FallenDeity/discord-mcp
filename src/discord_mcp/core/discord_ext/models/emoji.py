from __future__ import annotations

import discord
import pydantic

from .user import PartialUser

__all__: tuple[str, ...] = ("Emoji",)


class Emoji(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the emoji.")
    name: str | None = pydantic.Field(default=None, description="The name of the emoji.")
    animated: bool = pydantic.Field(description="Whether the emoji is animated.")
    roles: list[str] = pydantic.Field(default_factory=list, description="List of role IDs that can use this emoji.")
    user: PartialUser | None = pydantic.Field(default=None, description="The user who created the emoji, if available.")
    require_colons: bool = pydantic.Field(description="Whether the emoji requires colons to be used.")
    managed: bool = pydantic.Field(description="Whether the emoji is managed by an integration.")
    available: bool = pydantic.Field(description="Whether the emoji is available for use.")

    @classmethod
    def from_discord_emoji(cls, emoji: discord.Emoji | discord.PartialEmoji) -> Emoji:
        """Create an `Emoji` instance from a `discord.Emoji` or `discord.PartialEmoji` instance."""
        user = PartialUser.from_discord_user(emoji.user) if isinstance(emoji, discord.Emoji) and emoji.user else None
        return cls(
            id=str(emoji.id),
            name=emoji.name,
            animated=emoji.animated,
            roles=[str(role.id) for role in emoji.roles] if isinstance(emoji, discord.Emoji) else [],
            user=user,
            require_colons=emoji.require_colons if isinstance(emoji, discord.Emoji) else False,
            managed=emoji.managed if isinstance(emoji, discord.Emoji) else False,
            available=emoji.available if isinstance(emoji, discord.Emoji) else True,
        )
