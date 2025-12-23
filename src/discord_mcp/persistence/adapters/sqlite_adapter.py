from __future__ import annotations

import logging
import typing as t
from contextlib import asynccontextmanager
from types import TracebackType

import aiosqlite
from mcp.server.streamable_http import EventId
from mcp.types import JSONRPCMessage

from discord_mcp.persistence.adapters.base import EventStoreAdapter
from discord_mcp.persistence.models.events import EventRecord

__all__: tuple[str, ...] = ("SQLiteAdapeter",)


logger = logging.getLogger(__name__)


class SQLiteAdapeter(EventStoreAdapter):

    def __init__(self, db: str = "event_store.db") -> None:
        self._db_path = db

    async def __aenter__(self) -> SQLiteAdapeter:
        logger.info(f"Connected to SQLite database at {self._db_path}")
        await self.init_schema()
        logger.info("SQLite database schema initialized.")
        return self

    async def __aexit__(
        self,
        exc_type: t.Optional[type[BaseException]],
        exc_value: t.Optional[BaseException],
        traceback: t.Optional[TracebackType],
    ) -> None:
        logger.info("SQLiteAdapter cleanup complete.")

    async def init_schema(self) -> None:  # type: ignore
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    stream_id TEXT NOT NULL,
                    message TEXT NULL,
                    created_at TIMESTAMP NOT NULL
                )
                """
            )

    @asynccontextmanager
    async def get_cursor(self) -> t.AsyncGenerator[aiosqlite.Cursor, None]:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.cursor() as cursor:
                yield cursor
            await db.commit()

    async def insert_event(self, event: EventRecord) -> None:
        async with self.get_cursor() as cursor:
            message_json = event.message.model_dump_json() if event.message is not None else None
            print(
                f"message_json: {message_json}, type: {type(message_json)}, event_id: {event.event_id}, stream_id: {event.stream_id}, created_at: {event.created_at}"
            )
            await cursor.execute(
                """
                INSERT INTO events (id, stream_id, message, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event.event_id, event.stream_id, message_json, event.created_at),
            )
        logger.info(f"Event {event.event_id} inserted successfully.")

    async def get_event(self, event_id: EventId) -> EventRecord | None:
        async with self.get_cursor() as cursor:
            logger.debug(f"Retrieving event with ID: {event_id}.")
            await cursor.execute(
                "SELECT id, stream_id, message, created_at FROM events WHERE id = ?",
                (event_id,),
            )
            row = await cursor.fetchone()
            if row:
                event = EventRecord(
                    event_id=row[0],
                    stream_id=row[1],
                    message=JSONRPCMessage.model_validate_json(row[2]),
                    created_at=row[3],
                )
                logger.info(f"Event {event_id} retrieved successfully.")
                return event
            logger.warning(f"Event {event_id} not found.")
            return None

    async def get_events_after(self, after_event_id: EventId) -> t.List[EventRecord]:
        logger.debug(f"Retrieving events after {after_event_id}.")
        last_event = await self.get_event(after_event_id)
        if not last_event:
            logger.warning(f"Event {after_event_id} not found, returning empty list.")
            return []
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, stream_id, message, created_at
                FROM events
                WHERE stream_id = ? AND created_at > ?
                ORDER BY created_at ASC
                """,
                (last_event.stream_id, last_event.created_at),
            )
            rows = await cursor.fetchall()
            events = [
                EventRecord(
                    event_id=row[0],
                    stream_id=row[1],
                    message=JSONRPCMessage.model_validate_json(row[2]),
                    created_at=row[3],
                )
                for row in rows
            ]
            logger.info(f"Retrieved {len(events)} events after {after_event_id} for stream {last_event.stream_id}.")
            return events
