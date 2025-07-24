import logging
import typing as t
from types import TracebackType

logger = logging.getLogger(__name__)


class BotProtocol(t.Protocol):
    async def __aenter__(self) -> "BotProtocol": ...

    async def __aexit__(
        self,
        exc_type: t.Optional[type[BaseException]],
        exc_val: t.Optional[BaseException],
        exc_tb: t.Optional[TracebackType],
    ) -> None: ...

    async def run(self) -> None: ...
