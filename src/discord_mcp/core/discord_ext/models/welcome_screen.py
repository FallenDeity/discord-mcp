import pydantic

__all__: tuple[str, ...] = (
    "WelcomeScreenChannel",
    "WelcomeScreen",
)


class WelcomeScreenChannel(pydantic.BaseModel):
    channel_id: str = pydantic.Field(description="The ID of the channel.")
    description: str = pydantic.Field(description="The description shown for the channel.")
    emoji_id: str | None = pydantic.Field(
        default=None, description="The ID of the emoji shown for the channel, if any."
    )
    emoji_name: str | None = pydantic.Field(
        default=None, description="The name of the emoji shown for the channel, if any."
    )


class WelcomeScreen(pydantic.BaseModel):
    description: str | None = pydantic.Field(
        default=None, description="The server description shown in the welcome screen."
    )
    welcome_channels: list[WelcomeScreenChannel] = pydantic.Field(
        default_factory=list[WelcomeScreenChannel], description="The channels shown in the welcome screen."
    )
