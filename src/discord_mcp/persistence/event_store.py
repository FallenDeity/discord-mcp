import logging

from mcp.server.streamable_http import EventCallback, EventId, EventMessage, EventStore, StreamId
from mcp.types import JSONRPCMessage

from discord_mcp.persistence.adapters.base import EventStoreAdapter
from discord_mcp.persistence.models.events import EventRecord

__all__: tuple[str, ...] = ("PersistentEventStore",)


logger = logging.getLogger(__name__)


# TODO: Currently there is no cleanup logic for the event store, to clean up old events.
class PersistentEventStore(EventStore):
    def __init__(self, adapter: EventStoreAdapter) -> None:
        self._adapter = adapter

    async def store_event(self, stream_id: StreamId, message: JSONRPCMessage | None) -> EventId:
        async with self._adapter:
            event = EventRecord(
                stream_id=stream_id,
                message=message,
            )
            await self._adapter.insert_event(event)
            return event.event_id

    async def replay_events_after(self, last_event_id: EventId, send_callback: EventCallback) -> StreamId | None:
        async with self._adapter:
            events = await self._adapter.get_events_after(last_event_id)
            for event in events:
                if event.message is not None:
                    await send_callback(EventMessage(message=event.message, event_id=event.event_id))
            return events[-1].stream_id if events else None
