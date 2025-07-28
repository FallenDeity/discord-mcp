from __future__ import annotations

import logging
import typing as t

import discord
from discord.ext import commands

from discord_mcp.utils.env import ENV

if t.TYPE_CHECKING:
    from discord_mcp.utils.env import Environment


logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    def __init__(self, environment: Environment = ENV) -> None:
        intents = discord.Intents.all()
        self.environment = environment
        super().__init__(command_prefix="!", intents=intents, help_command=None)
