from __future__ import annotations

import datetime
import logging
import typing as t

import discord
from discord.ext import commands

from discord_mcp.utils.env import ENV

if t.TYPE_CHECKING:
    from discord_mcp.utils.env import Environment


logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    _start_time: datetime.datetime

    def __init__(self, environment: Environment = ENV) -> None:
        intents = discord.Intents.all()
        self.environment = environment
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        self._start_time = datetime.datetime.now(tz=datetime.timezone.utc)
        logger.info(f"Bot started at {self._start_time.isoformat()}")

    @property
    def uptime(self) -> datetime.timedelta:
        return datetime.datetime.now(tz=datetime.timezone.utc) - self._start_time
