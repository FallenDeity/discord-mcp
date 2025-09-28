from __future__ import annotations

import typing as t

import discord
import pydantic

__all__: tuple[str, ...] = ("PartialUser",)

NameplatePalette = t.Literal[
    "crimson",
    "berry",
    "sky",
    "teal",
    "forest",
    "bubble_gum",
    "violet",
    "cobalt",
    "clover",
    "lemon",
    "white",
]
PremiumType = t.Literal[0, 1, 2, 3]


class PrimaryGuild(pydantic.BaseModel):
    identity_guild_id: str = pydantic.Field(description="The ID of the user's primary guild.")
    identity_enabled: bool = pydantic.Field(description="Whether the primary guild is enabled.")
    tag: str = pydantic.Field(description="The user's tag in the primary guild.")
    badge: int = pydantic.Field(description="The badge level of the user in the primary guild.")


class UserSKU(pydantic.BaseModel):
    asset: str | None = pydantic.Field(description="The URL of the user's SKU asset, if available.", default=None)
    sku_id: int | None = pydantic.Field(description="The SKU ID of the user's asset, if available.", default=None)


AvatarDecorationData = UserSKU


class Collectible(UserSKU):
    label: str = pydantic.Field(description="The label of the collectible.")
    expires_at: str | None = pydantic.Field(
        default=None, description="The expiration timestamp of the collectible, if any."
    )


class NameplateCollectible(Collectible):
    palette: NameplatePalette = pydantic.Field(description="The color palette of the nameplate collectible.")


class UserCollectibles(pydantic.BaseModel):
    nameplate: NameplateCollectible | None = pydantic.Field(
        default=None, description="The user's nameplate collectible, if available."
    )


class PartialUser(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the user.")
    username: str = pydantic.Field(description="The user's username, not unique across the platform.")
    discriminator: str = pydantic.Field(
        description="The user's discriminator, a 4-digit number used to differentiate users with the same username. (deprecated)"
    )
    global_name: str | None = pydantic.Field(
        default=None, description="The user's global name, if set. For bots, this is the application name."
    )
    avatar: str | None = pydantic.Field(description="The URL of the user's avatar, if available.")
    avatar_decoration_data: AvatarDecorationData | None = pydantic.Field(
        default=None, description="The user's avatar decoration data, if available."
    )
    banner: str | None = pydantic.Field(default=None, description="The URL of the user's banner image, if available.")
    accent_color: int | None = pydantic.Field(
        default=None, description="The user's accent color as an integer representation of a hexadecimal color code."
    )
    primary_guild: PrimaryGuild | None = pydantic.Field(
        default=None, description="The user's primary guild information, if available."
    )
    collectibles: UserCollectibles | None = pydantic.Field(
        default=None, description="The user's collectibles information, if available."
    )

    @classmethod
    def from_discord_user(cls, user: discord.User) -> PartialUser:
        """Create a PartialUser instance from a discord.User object."""
        return cls(
            id=str(user.id),
            username=user.name,
            discriminator=user.discriminator,
            global_name=user.global_name,
            avatar=user.display_avatar.url if user.display_avatar else None,
            avatar_decoration_data=(
                AvatarDecorationData(asset=user.avatar_decoration.url, sku_id=user.avatar_decoration_sku_id)
                if user.avatar_decoration
                else None
            ),
            banner=user.banner.url if user.banner else None,
            accent_color=(user.accent_color.value if user.accent_color else None),
        )


class User(PartialUser):
    bot: bool | None = pydantic.Field(description="Whether the user is a bot.", default=None)
    system: bool | None = pydantic.Field(
        description="Whether the user is a system user/official Discord account.", default=None
    )
    mfa_enabled: bool | None = pydantic.Field(
        description="Whether the user has two-factor authentication enabled.", default=None
    )
    locale: str | None = pydantic.Field(default=None, description="The user's chosen language option, if available.")
    verified: bool | None = pydantic.Field(
        default=None, description="Whether the email on the user's account has been verified, if available."
    )
    email: str | None = pydantic.Field(default=None, description="The user's email address, if available.")
    flags: int | None = pydantic.Field(
        default=None, description="The flags for the user, such as 'Verified', 'Partner', etc."
    )
    premium_type: PremiumType | None = pydantic.Field(
        default=None,
        description="The type of Nitro subscription on the user's account, if any. 0 for None, 1 for Nitro Classic, 2 for Nitro, 3 for Nitro Basic.",
    )
    public_flags: int | None = pydantic.Field(
        default=None, description="The public flags for the user, such as 'Staff', 'Partner', etc."
    )
