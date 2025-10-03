from __future__ import annotations

import enum
import typing as t

import discord
import pydantic

from .user import PartialUser

__all__: tuple[str, ...] = (
    "MembershipState",
    "TeamMember",
    "Team",
)


class MembershipState(enum.StrEnum):
    INVITED = "invited"
    ACCEPTED = "accepted"


class TeamMember(pydantic.BaseModel):
    user: PartialUser = pydantic.Field(description="The user who is a member of the team.")
    membership_state: MembershipState = pydantic.Field(description="The state of the user's membership in the team.")
    permissions: list[str] = pydantic.Field(description="The permissions the user has in the team.")
    team_id: str = pydantic.Field(description="The ID of the team the user is a member of.")
    role: t.Literal["admin", "developer", "read_only"] = pydantic.Field(description="The role of the user in the team.")

    @classmethod
    def from_discord_team_member(cls, member: discord.TeamMember) -> TeamMember:
        return cls(
            user=PartialUser.from_discord_user(member),
            membership_state=MembershipState(member.membership_state.name.lower()),
            permissions=member.permissions,
            team_id=str(member.team.id),
            role=member.role.name,
        )


class Team(pydantic.BaseModel):
    id: str = pydantic.Field(description="The unique ID of the team.")
    icon: str | None = pydantic.Field(default=None, description="The icon hash of the team, if any.")
    name: str = pydantic.Field(description="The name of the team.")
    members: list[TeamMember] = pydantic.Field(description="The members of the team.")
    owner_user_id: str = pydantic.Field(description="The user ID of the owner of the team.")

    @classmethod
    def from_discord_team(cls, team: discord.Team) -> Team:
        return cls(
            id=str(team.id),
            icon=team.icon.url if team.icon else None,
            name=team.name,
            members=[TeamMember.from_discord_team_member(member) for member in team.members],
            owner_user_id=str(team.owner_id),
        )
