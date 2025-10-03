from __future__ import annotations

import enum
import typing as t

import discord
import pydantic

from .team import Team
from .user import User

__all__: tuple[str, ...] = (
    "AppIntegrationType",
    "InstallParams",
    "ApplicationIntegrationTypeConfig",
    "BaseAppInfo",
    "AppInfo",
    "PartialAppInfo",
)


AppInfoT = t.TypeVar("AppInfoT", bound=discord.AppInfo | discord.PartialAppInfo)


class AppIntegrationType(enum.StrEnum):
    GUILD_INSTALL = "guild_install"
    USER_INSTALL = "user_install"

    @classmethod
    def from_discord_integration_type(cls, integration_type: t.Literal["0", "1"]) -> AppIntegrationType:
        if integration_type == "0":
            return cls.GUILD_INSTALL
        elif integration_type == "1":
            return cls.USER_INSTALL
        else:
            raise ValueError(f"Unknown integration type: {integration_type}")


class InstallParams(pydantic.BaseModel):
    scopes: list[str] = pydantic.Field(description="The OAuth2 scopes for the application.")
    permissions: list[str] = pydantic.Field(description="The permissions integer for the application.")

    @classmethod
    def from_discord_install_params(cls, params: discord.AppInstallParams) -> InstallParams:
        return cls(
            scopes=params.scopes,
            permissions=[name for name, value in params.permissions if value],
        )


class ApplicationIntegrationTypeConfig(pydantic.BaseModel):
    oauth2_install_params: InstallParams | None = pydantic.Field(
        default=None, description="The OAuth2 installation parameters for the application."
    )

    @classmethod
    def from_discord_integration_type_config(
        cls, config: discord.IntegrationTypeConfig
    ) -> ApplicationIntegrationTypeConfig:
        return cls(
            oauth2_install_params=(
                InstallParams.from_discord_install_params(config.oauth2_install_params)
                if config.oauth2_install_params
                else None
            ),
        )


class BaseAppInfo(pydantic.BaseModel, t.Generic[AppInfoT]):
    id: str = pydantic.Field(description="The unique ID of the application.")
    name: str = pydantic.Field(description="The name of the application.")
    icon: str | None = pydantic.Field(default=None, description="The icon hash of the application, if any.")
    description: str = pydantic.Field(description="The description of the application.")
    summary: str = pydantic.Field(description="The summary of the application.")
    verify_key: str = pydantic.Field(
        description="The hex-encoded key for verification in interactions and the GameSDK."
    )
    flags: list[str] = pydantic.Field(description="The flags for the application.")
    approximate_user_install_count: int | None = pydantic.Field(
        default=None, description="The approximate number of users that have installed the application."
    )
    cover_image: str | None = pydantic.Field(
        default=None, description="The cover image hash of the application, if any."
    )
    terms_of_service_url: str | None = pydantic.Field(
        default=None, description="The URL of the application's terms of service, if any."
    )
    privacy_policy_url: str | None = pydantic.Field(
        default=None, description="The URL of the application's privacy policy, if any."
    )
    rpc_origins: list[str] | None = pydantic.Field(
        default=None, description="The RPC origin URLs for the application, if any."
    )
    interactions_endpoint_url: str | None = pydantic.Field(
        default=None, description="The URL of the application's interactions endpoint, if any."
    )
    redirect_uris: list[str] | None = pydantic.Field(
        default=None, description="The redirect URIs for the application, if any."
    )
    role_connections_verification_url: str | None = pydantic.Field(
        default=None, description="The URL for role connections verification for the application, if any."
    )

    @classmethod
    def from_discord_app_info(cls, app_info: AppInfoT) -> BaseAppInfo[AppInfoT]:
        return cls(
            id=str(app_info.id),
            name=app_info.name,
            icon=app_info.icon.url if app_info.icon else None,
            description=app_info.description,
            summary="",
            verify_key=app_info.verify_key,
            flags=[name for name, value in app_info.flags if value],
            approximate_user_install_count=(
                app_info.approximate_user_install_count if isinstance(app_info, discord.AppInfo) else None
            ),
            cover_image=app_info.cover_image.url if app_info.cover_image else None,
            terms_of_service_url=app_info.terms_of_service_url,
            privacy_policy_url=app_info.privacy_policy_url,
            rpc_origins=app_info.rpc_origins,
            interactions_endpoint_url=app_info.interactions_endpoint_url,
            redirect_uris=app_info.redirect_uris,
            role_connections_verification_url=app_info.role_connections_verification_url,
        )


class AppInfo(BaseAppInfo[discord.AppInfo]):
    owner: User | None = pydantic.Field(default=None, description="The user who owns the application, if any.")
    bot_public: bool = pydantic.Field(description="Whether the application's bot is public.")
    bot_require_code_grant: bool = pydantic.Field(description="Whether the application's bot requires a code grant.")
    team: Team | None = pydantic.Field(default=None, description="The team that owns the application, if any.")
    guild_id: str | None = pydantic.Field(
        default=None, description="The ID of the guild the application belongs to, if any."
    )
    primary_sku_id: str | None = pydantic.Field(
        default=None, description="The ID of the primary SKU for the application, if any."
    )
    slug: str | None = pydantic.Field(default=None, description="The slug of the application, if any.")
    hook: bool | None = pydantic.Field(default=None, description="Whether the application is a game sold on Discord.")
    max_participants: int | None = pydantic.Field(
        default=None, description="The maximum number of participants for the application, if any."
    )
    tags: list[str] | None = pydantic.Field(
        default=None, description="The tags for the application to show in the Discord client, if any."
    )
    install_params: InstallParams | None = pydantic.Field(
        default=None, description="The installation parameters for the application, if any."
    )
    custom_install_url: str | None = pydantic.Field(
        default=None, description="The custom installation URL for the application, if any."
    )
    integration_type_config: dict[AppIntegrationType, ApplicationIntegrationTypeConfig] | None = pydantic.Field(
        default=None, description="The integration type configuration for the application, if any."
    )

    @classmethod
    def from_discord_appinfo(cls, app_info: discord.AppInfo) -> AppInfo:
        return cls(
            **BaseAppInfo.from_discord_app_info(app_info).model_dump(),
            owner=User.from_discord_user(app_info.owner) if app_info.owner else None,
            bot_public=app_info.bot_public,
            bot_require_code_grant=app_info.bot_require_code_grant,
            team=Team.from_discord_team(app_info.team) if app_info.team else None,
            guild_id=str(app_info.guild.id) if app_info.guild else None,
            primary_sku_id=str(app_info.primary_sku_id) if app_info.primary_sku_id else None,
            slug=app_info.slug,
            hook=None,
            max_participants=None,
            tags=app_info.tags,
            install_params=(
                InstallParams.from_discord_install_params(app_info.install_params) if app_info.install_params else None
            ),
            custom_install_url=app_info.custom_install_url,
            integration_type_config={
                AppIntegrationType.from_discord_integration_type(
                    config_type
                ): ApplicationIntegrationTypeConfig.from_discord_integration_type_config(
                    discord.IntegrationTypeConfig(config)
                )
                for config_type, config in app_info._integration_types_config.items()
            },
        )


class PartialAppInfo(BaseAppInfo[discord.PartialAppInfo]):
    hook: bool | None = pydantic.Field(default=None, description="Whether the application is a game sold on Discord.")
    max_participants: int | None = pydantic.Field(
        default=None, description="The maximum number of participants for the application, if any."
    )
    approximate_guild_count: int | None = pydantic.Field(
        default=None, description="The approximate number of guilds the application is in, if any."
    )

    @classmethod
    def from_discord_appinfo(cls, app_info: discord.PartialAppInfo) -> PartialAppInfo:
        return cls(
            **BaseAppInfo.from_discord_app_info(app_info).model_dump(),
            hook=None,
            max_participants=None,
            approximate_guild_count=app_info.approximate_guild_count,
        )
