from __future__ import annotations

import discord
import pydantic

__all__: tuple[str, ...] = ("ForumTag",)


class ForumTag(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the tag.")
    name: str = pydantic.Field(description="The name of the tag.")
    moderated: bool = pydantic.Field(description="Whether the tag is moderated.")
    emoji_id: str | None = pydantic.Field(default=None, description="The ID of the emoji for the tag, if custom.")
    emoji_name: str | None = pydantic.Field(default=None, description="The name of the emoji for the tag.")

    @classmethod
    def from_discord_forum_tag(cls, tag: discord.ForumTag) -> ForumTag:
        return cls(
            id=str(tag.id),
            name=tag.name,
            moderated=tag.moderated,
            emoji_id=str(tag.emoji.id) if tag.emoji and tag.emoji.id else None,
            emoji_name=tag.emoji.name if tag.emoji else None,
        )
