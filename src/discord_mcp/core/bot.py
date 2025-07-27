from __future__ import annotations

import logging
import typing as t

import discord
from discord.ext import commands

from discord_mcp.utils.env import ENV

# from discord_mcp.utils.logger import setup_logging

if t.TYPE_CHECKING:
    from discord_mcp.utils.env import Environment


logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    def __init__(
        self, environment: Environment = ENV, logging_level: int = logging.INFO, file_logging: bool = False
    ) -> None:
        intents = discord.Intents.all()
        self.environment = environment
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        # setup_logging(package_name="discord", level=logging_level, file_logging=file_logging)
