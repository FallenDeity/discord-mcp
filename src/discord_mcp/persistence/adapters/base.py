import abc
import typing as t
from types import TracebackType

from mcp.server.streamable_http import EventId

from discord_mcp.persistence.models.events import EventRecord

__all__: tuple[str, ...] = ("EventStoreAdapter",)


class EventStoreAdapter(abc.ABC):
    @abc.abstractmethod
    async def __aenter__(self) -> "EventStoreAdapter":
        """Initialize the adapter."""
        pass

    @abc.abstractmethod
    async def __aexit__(
        self,
        exc_type: t.Optional[type[BaseException]],
        exc_value: t.Optional[BaseException],
        traceback: t.Optional[TracebackType],
    ) -> None:
        """Clean up the adapter."""
        pass

    @abc.abstractmethod
    async def init_schema(self) -> None:
        """Initialize the database schema for the event store."""
        pass

    @abc.abstractmethod
    async def insert_event(self, event: EventRecord) -> None:
        """Insert a new event record into the store."""
        pass

    @abc.abstractmethod
    async def get_event(self, event_id: EventId) -> EventRecord | None:
        """Retrieve a specific event record by its ID."""
        pass

    @abc.abstractmethod
    async def get_events_after(self, after_event_id: EventId) -> t.List[EventRecord]:
        """Retrieve all event records for a specific stream after a specific event."""
        pass
