import datetime
import uuid

import attrs
from mcp.server.streamable_http import EventId, StreamId
from mcp.types import JSONRPCMessage

__all__: tuple[str, ...] = ("EventRecord",)


@attrs.define
class EventRecord:
    stream_id: StreamId
    message: JSONRPCMessage
    event_id: EventId = attrs.field(factory=lambda: str(uuid.uuid4()))
    created_at: datetime.datetime = attrs.field(
        factory=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
