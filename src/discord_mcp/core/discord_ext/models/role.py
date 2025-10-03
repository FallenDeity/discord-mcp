from __future__ import annotations

import discord
import pydantic

__all__: tuple[str, ...] = (
    "RoleColors",
    "RoleTags",
    "Role",
)


class RoleColors(pydantic.BaseModel):
    primary: int = pydantic.Field(description="The primary color of the role in integer format.")
    secondary: int | None = pydantic.Field(
        default=None,
        description="The secondary color of the role in integer format, if any. This will make the role a gradient between the other provided colors.",
    )
    tertiary: int | None = pydantic.Field(
        default=None,
        description="The tertiary color of the role in integer format, if any.  This will turn the gradient into a holographic style.",
    )


class RoleTags(pydantic.BaseModel):
    bot_id: str | None = pydantic.Field(default=None, description="The ID of the bot this role belongs to, if any.")
    integration_id: str | None = pydantic.Field(
        default=None, description="The ID of the integration this role belongs to, if any."
    )
    subscription_listing_id: str | None = pydantic.Field(
        default=None, description="The ID of the subscription listing this role belongs to, if any."
    )
    premium_subscriber: bool | None = pydantic.Field(
        default=None, description="Whether this role is the guild's premium subscriber role."
    )
    available_for_purchase: bool | None = pydantic.Field(
        default=None, description="Whether this role is available for purchase."
    )
    guild_connections: bool | None = pydantic.Field(
        default=None, description="Whether this role is a guild connections or guild's linked role."
    )

    @classmethod
    def from_discord_role_tags(cls, tags: discord.RoleTags) -> RoleTags:
        """Create a `RoleTags` instance from a `discord.RoleTags` instance."""
        return cls(
            bot_id=str(tags.bot_id) if tags.bot_id else None,
            integration_id=str(tags.integration_id) if tags.integration_id else None,
            subscription_listing_id=str(tags.subscription_listing_id) if tags.subscription_listing_id else None,
            premium_subscriber=tags.is_premium_subscriber(),
            available_for_purchase=tags.is_available_for_purchase(),
            guild_connections=tags.is_guild_connection(),
        )


class Role(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the role.")
    name: str = pydantic.Field(description="The name of the role.")
    color: int = pydantic.Field(
        description="The color of the role in integer format. (deprecated, use color_data.primary instead)"
    )
    color_data: RoleColors = pydantic.Field(description="The color information of the role.")
    hoist: bool = pydantic.Field(description="Whether the role is displayed separately in the member list.")
    position: int = pydantic.Field(description="The position of the role in the role hierarchy.")
    permissions: list[str] = pydantic.Field(description="The permissions for the role.")
    managed: bool = pydantic.Field(description="Whether the role is managed by an integration.")
    mentionable: bool = pydantic.Field(description="Whether the role is mentionable.")
    flags: list[str] = pydantic.Field(description="The flags for the role.")
    icon: str | None = pydantic.Field(default=None, description="The icon hash of the role, if any.")
    unicode_emoji: str | None = pydantic.Field(default=None, description="The unicode emoji of the role, if any.")
    tags: RoleTags | None = pydantic.Field(default=None, description="The tags associated with the role, if any.")

    @classmethod
    def from_discord_role(cls, role: discord.Role) -> Role:
        """Create a `Role` instance from a `discord.Role` instance."""
        return cls(
            id=str(role.id),
            name=role.name,
            color=role.color.value,
            color_data=RoleColors(
                primary=role.color.value,
                secondary=role.secondary_color.value if role.secondary_color else None,
                tertiary=role.tertiary_color.value if role.tertiary_color else None,
            ),
            hoist=role.hoist,
            position=role.position,
            permissions=[name for name, value in role.permissions if value],
            managed=role.managed,
            mentionable=role.mentionable,
            flags=[name for name, value in role.flags if value],
            icon=role.icon.url if role.icon else None,
            unicode_emoji=role.unicode_emoji,
            tags=RoleTags.from_discord_role_tags(role.tags) if role.tags else None,
        )
