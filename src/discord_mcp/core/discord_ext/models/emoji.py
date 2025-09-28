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
