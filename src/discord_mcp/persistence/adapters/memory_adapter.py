import collections
import logging
import typing as t
from types import TracebackType

from mcp.server.streamable_http import EventId, StreamId

from discord_mcp.persistence.adapters.base import EventStoreAdapter
from discord_mcp.persistence.models.events import EventRecord

__all__: tuple[str, ...] = ("InMemoryAdapter",)


logger = logging.getLogger(__name__)


class InMemoryAdapter(EventStoreAdapter):
    def __init__(self) -> None:
        self._streams: t.Dict[StreamId, collections.deque[EventRecord]] = collections.defaultdict(collections.deque)
        self._events: t.Dict[EventId, EventRecord] = {}

    async def __aenter__(self) -> "InMemoryAdapter":
        logger.info("InMemoryAdapter initialized.")
        return self

    async def __aexit__(
        self,
        exc_type: t.Optional[type[BaseException]],
        exc_value: t.Optional[BaseException],
        traceback: t.Optional[TracebackType],
    ) -> None:
        logger.info("InMemoryAdapter cleanup complete.")

    async def init_schema(self) -> None:
        logger.info("InMemoryAdapter schema initialized (no-op).")

    async def insert_event(self, event: EventRecord) -> None:
        self._streams[event.stream_id].append(event)
        self._events[event.event_id] = event

    async def get_event(self, event_id: EventId) -> EventRecord | None:
        return self._events.get(event_id)

    async def get_events_after(self, after_event_id: EventId) -> t.List[EventRecord]:
        if after_event_id not in self._events:
            return []

        after_event = self._events[after_event_id]
        stream_events = self._streams[after_event.stream_id]
        return [event for event in stream_events if event.created_at > after_event.created_at]
