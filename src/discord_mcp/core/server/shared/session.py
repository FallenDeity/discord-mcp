import logging

import anyio
from mcp.server.session import ServerSession
from mcp.shared.message import SessionMessage
from mcp.shared.session import RequestResponder
from mcp.types import (
    CONNECTION_CLOSED,
    INVALID_PARAMS,
    CancelledNotification,
    ErrorData,
    JSONRPCError,
    JSONRPCMessage,
    JSONRPCNotification,
    JSONRPCRequest,
    ProgressNotification,
)

__all__: tuple[str, ...] = ("DiscordMCPServerSession",)


logger = logging.getLogger(__name__)


class DiscordMCPServerSession(ServerSession):
    async def _receive_loop(self) -> None:
        async with self._incoming_message_stream_writer:
            async with (
                self._read_stream,
                self._write_stream,
            ):
                try:
                    async for message in self._read_stream:
                        if isinstance(message, Exception):
                            await self._handle_incoming(message)
                        elif isinstance(message.message.root, JSONRPCRequest):
                            try:
                                validated_request = self._receive_request_type.model_validate(
                                    message.message.root.model_dump(by_alias=True, mode="json", exclude_none=True)
                                )
                                responder = RequestResponder(
                                    request_id=message.message.root.id,
                                    request_meta=(
                                        validated_request.root.params.meta if validated_request.root.params else None
                                    ),
                                    request=validated_request,
                                    session=self,
                                    on_complete=lambda r: self._in_flight.pop(r.request_id, None),
                                    message_metadata=message.metadata,
                                )
                                self._in_flight[responder.request_id] = responder
                                await self._received_request(responder)

                                if not responder._completed:  # type: ignore[reportPrivateUsage]
                                    await self._handle_incoming(responder)
                            except Exception as e:
                                # For request validation errors, send a proper JSON-RPC error
                                # response instead of crashing the server
                                logger.warning(f"Failed to validate request: {e}")
                                logger.debug(f"Message that failed validation: {message.message.root}")
                                error_response = JSONRPCError(
                                    jsonrpc="2.0",
                                    id=message.message.root.id,
                                    error=ErrorData(
                                        code=INVALID_PARAMS,
                                        message="Invalid request parameters",
                                        data="",
                                    ),
                                )
                                session_message = SessionMessage(message=JSONRPCMessage(error_response))
                                await self._write_stream.send(session_message)

                        elif isinstance(message.message.root, JSONRPCNotification):
                            try:
                                notification = self._receive_notification_type.model_validate(
                                    message.message.root.model_dump(by_alias=True, mode="json", exclude_none=True)
                                )
                                notification.__dict__["metadata"] = message.metadata
                                # add the field to the notification
                                # Handle cancellation notifications
                                if isinstance(notification.root, CancelledNotification):
                                    cancelled_id = notification.root.params.requestId
                                    if cancelled_id in self._in_flight:
                                        await self._in_flight[cancelled_id].cancel()
                                else:
                                    # Handle progress notifications callback
                                    if isinstance(notification.root, ProgressNotification):
                                        progress_token = notification.root.params.progressToken
                                        # If there is a progress callback for this token,
                                        # call it with the progress information
                                        if progress_token in self._progress_callbacks:
                                            callback = self._progress_callbacks[progress_token]
                                            await callback(
                                                notification.root.params.progress,
                                                notification.root.params.total,
                                                notification.root.params.message,
                                            )
                                    await self._received_notification(notification)
                                    await self._handle_incoming(notification)
                            except Exception as e:
                                # For other validation errors, log and continue
                                logger.warning(
                                    f"Failed to validate notification: {e}. Message was: {message.message.root}"
                                )
                        else:  # Response or error
                            stream = self._response_streams.pop(message.message.root.id, None)
                            if stream:
                                await stream.send(message.message.root)
                            else:
                                await self._handle_incoming(
                                    RuntimeError(f"Received response with an unknown request ID: {message}")
                                )

                except anyio.ClosedResourceError:
                    # This is expected when the client disconnects abruptly.
                    # Without this handler, the exception would propagate up and
                    # crash the server's task group.
                    logger.debug("Read stream closed by client")
                except Exception as e:
                    # Other exceptions are not expected and should be logged. We purposefully
                    # catch all exceptions here to avoid crashing the server.
                    logger.exception(f"Unhandled exception in receive loop: {e}")
                finally:
                    # after the read stream is closed, we need to send errors
                    # to any pending requests
                    for id, stream in self._response_streams.items():
                        error = ErrorData(code=CONNECTION_CLOSED, message="Connection closed")
                        try:
                            await stream.send(JSONRPCError(jsonrpc="2.0", id=id, error=error))
                            await stream.aclose()
                        except Exception:
                            # Stream might already be closed
                            pass
                    self._response_streams.clear()
