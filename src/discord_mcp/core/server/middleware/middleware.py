from __future__ import annotations

import datetime
import functools
import logging
import typing as t

import attrs
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    CancelledNotification,
    CompleteRequest,
    CompleteResult,
    EmptyResult,
    GetPromptRequest,
    GetPromptResult,
    InitializedNotification,
    InitializeRequest,
    InitializeResult,
    ListPromptsRequest,
    ListPromptsResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListResourceTemplatesRequest,
    ListResourceTemplatesResult,
    ListToolsRequest,
    ListToolsResult,
    Notification,
    PingRequest,
    ProgressNotification,
    ReadResourceRequest,
    ReadResourceResult,
    Request,
    Result,
    RootsListChangedNotification,
    SetLevelRequest,
    SubscribeRequest,
    UnsubscribeRequest,
)

from discord_mcp.core.server.common.context import DiscordMCPContext, get_context
from discord_mcp.utils.enums import MiddlewareEventTypes, MiddlewareNotificationMethods, MiddlewareRequestMethods

MessageT = t.TypeVar("MessageT", bound=Request[t.Any, t.Any] | Notification[t.Any, t.Any])
ResultT = t.TypeVar("ResultT", bound=Result | None, covariant=True)


logger = logging.getLogger(__name__)


__all__: tuple[str, ...] = (
    "MiddlewareContext",
    "CallNext",
    "Middleware",
)


@attrs.define(kw_only=True, frozen=True)
class MiddlewareContext(t.Generic[MessageT]):
    context: DiscordMCPContext
    message: MessageT
    method: MiddlewareRequestMethods | MiddlewareNotificationMethods
    event_type: MiddlewareEventTypes = attrs.field(default=MiddlewareEventTypes.REQUEST)
    timestamp: datetime.datetime = attrs.field(factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    @classmethod
    def from_message(cls, message: MessageT) -> MiddlewareContext[MessageT]:
        is_request = isinstance(message, Request)
        return cls(
            context=get_context(),
            message=message,
            method=(
                MiddlewareRequestMethods(message.method)
                if is_request
                else MiddlewareNotificationMethods(message.method)
            ),
            event_type=MiddlewareEventTypes.REQUEST if is_request else MiddlewareEventTypes.NOTIFICATION,
        )

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}(context={self.context.request_context}, "
            f"message={self.message}, method={self.method}, "
            f"event_type={self.event_type}, timestamp={self.timestamp.isoformat()})"
        )


class CallNext(t.Protocol, t.Generic[MessageT, ResultT]):
    @t.overload
    def __call__(self, message: MessageT) -> t.Awaitable[ResultT]: ...
    @t.overload
    def __call__(self, ctx: MiddlewareContext[MessageT]) -> t.Awaitable[ResultT]: ...


class Middleware:
    async def __call__(
        self, message: MessageT | MiddlewareContext[MessageT], call_next: CallNext[MessageT, ResultT]
    ) -> ResultT:
        middleware_ctx = (
            message if isinstance(message, MiddlewareContext) else MiddlewareContext[MessageT].from_message(message)
        )
        chain = self._dispatch(middleware_ctx, call_next)
        return await chain(middleware_ctx)

    def _dispatch(self, ctx: MiddlewareContext[t.Any], call_next: CallNext[t.Any, t.Any]) -> CallNext[t.Any, t.Any]:
        _request_handlers: dict[
            MiddlewareRequestMethods,
            t.Callable[[MiddlewareContext[t.Any], CallNext[t.Any, t.Any]], t.Awaitable[Result]],
        ] = {
            MiddlewareRequestMethods.LIST_TOOLS: self.on_list_tools,
            MiddlewareRequestMethods.CALL_TOOL: self.on_call_tool,
            MiddlewareRequestMethods.READ_RESOURCE: self.on_read_resource,
            MiddlewareRequestMethods.GET_PROMPT: self.on_get_prompt,
            MiddlewareRequestMethods.LIST_RESOURCES: self.on_list_resources,
            MiddlewareRequestMethods.LIST_RESOURCE_TEMPLATES: self.on_list_resource_templates,
            MiddlewareRequestMethods.LIST_PROMPTS: self.on_list_prompts,
            MiddlewareRequestMethods.INITIALIZE: self.on_initialize,
            MiddlewareRequestMethods.PING: self.on_ping,
            MiddlewareRequestMethods.RESOURCES_SUBSCRIBE: self.on_resources_subscribe,
            MiddlewareRequestMethods.RESOURCES_UNSUBSCRIBE: self.on_resources_unsubscribe,
            MiddlewareRequestMethods.SET_LEVEL: self.on_set_level,
            MiddlewareRequestMethods.COMPLETE: self.on_complete,
        }
        _notification_handlers: dict[
            MiddlewareNotificationMethods,
            t.Callable[[MiddlewareContext[t.Any], CallNext[t.Any, t.Any]], t.Awaitable[None]],
        ] = {
            MiddlewareNotificationMethods.INITIALIZED: self.on_initialized,
            MiddlewareNotificationMethods.ROOTS_LIST_CHANGED: self.on_roots_list_changed,
            MiddlewareNotificationMethods.PROGRESS: self.on_progress,
            MiddlewareNotificationMethods.CANCELLED: self.on_cancelled,
        }
        match ctx.event_type:
            case MiddlewareEventTypes.REQUEST:
                specific_handler, event_handler = (
                    _request_handlers.get(t.cast(MiddlewareRequestMethods, ctx.method)),
                    self.on_request,
                )
            case MiddlewareEventTypes.NOTIFICATION:
                specific_handler, event_handler = (
                    _notification_handlers.get(t.cast(MiddlewareNotificationMethods, ctx.method)),
                    self.on_notification,
                )

        if specific_handler is None:
            raise ValueError(f"Unsupported method: {ctx.method} for event type: {ctx.event_type}")

        handler = functools.partial(specific_handler, call_next=call_next)
        handler = functools.partial(event_handler, call_next=handler)
        return functools.partial(self.on_message, call_next=handler)

    async def on_request(
        self,
        ctx: MiddlewareContext[Request[t.Any, t.Any]],
        call_next: CallNext[Request[t.Any, t.Any], Result],
    ) -> Result:
        """Handle a request."""
        return await call_next(ctx)

    async def on_notification(
        self,
        ctx: MiddlewareContext[Notification[t.Any, t.Any]],
        call_next: CallNext[Notification[t.Any, t.Any], None],
    ) -> None:
        """Handle a notification."""
        return await call_next(ctx)

    async def on_message(
        self,
        ctx: MiddlewareContext[Request[t.Any, t.Any] | Notification[t.Any, t.Any]],
        call_next: CallNext[Request[t.Any, t.Any] | Notification[t.Any, t.Any], Result | None],
    ) -> Result | None:
        """Handle a message, which can be either a request or a notification."""
        return await call_next(ctx)

    async def on_list_tools(
        self,
        ctx: MiddlewareContext[ListToolsRequest],
        call_next: CallNext[ListToolsRequest, ListToolsResult],
    ) -> ListToolsResult:
        return await call_next(ctx)

    async def on_call_tool(
        self,
        ctx: MiddlewareContext[CallToolRequest],
        call_next: CallNext[CallToolRequest, CallToolResult],
    ) -> CallToolResult:
        return await call_next(ctx)

    async def on_read_resource(
        self,
        ctx: MiddlewareContext[ReadResourceRequest],
        call_next: CallNext[ReadResourceRequest, ReadResourceResult],
    ) -> ReadResourceResult:
        return await call_next(ctx)

    async def on_get_prompt(
        self,
        ctx: MiddlewareContext[GetPromptRequest],
        call_next: CallNext[GetPromptRequest, GetPromptResult],
    ) -> GetPromptResult:
        return await call_next(ctx)

    async def on_list_resources(
        self,
        ctx: MiddlewareContext[ListResourcesRequest],
        call_next: CallNext[ListResourcesRequest, ListResourcesResult],
    ) -> ListResourcesResult:
        return await call_next(ctx)

    async def on_list_resource_templates(
        self,
        ctx: MiddlewareContext[ListResourceTemplatesRequest],
        call_next: CallNext[ListResourceTemplatesRequest, ListResourceTemplatesResult],
    ) -> ListResourceTemplatesResult:
        return await call_next(ctx)

    async def on_list_prompts(
        self,
        ctx: MiddlewareContext[ListPromptsRequest],
        call_next: CallNext[ListPromptsRequest, ListPromptsResult],
    ) -> ListPromptsResult:
        return await call_next(ctx)

    async def on_initialize(
        self,
        ctx: MiddlewareContext[InitializeRequest],
        call_next: CallNext[InitializeRequest, InitializeResult],
    ) -> InitializeResult:
        return await call_next(ctx)

    async def on_ping(
        self,
        ctx: MiddlewareContext[PingRequest],
        call_next: CallNext[PingRequest, EmptyResult],
    ) -> EmptyResult:
        return await call_next(ctx)

    async def on_resources_subscribe(
        self,
        ctx: MiddlewareContext[SubscribeRequest],
        call_next: CallNext[SubscribeRequest, EmptyResult],
    ) -> EmptyResult:
        return await call_next(ctx)

    async def on_resources_unsubscribe(
        self,
        ctx: MiddlewareContext[UnsubscribeRequest],
        call_next: CallNext[UnsubscribeRequest, EmptyResult],
    ) -> EmptyResult:
        return await call_next(ctx)

    async def on_set_level(
        self,
        ctx: MiddlewareContext[SetLevelRequest],
        call_next: CallNext[SetLevelRequest, EmptyResult],
    ) -> EmptyResult:
        return await call_next(ctx)

    async def on_complete(
        self,
        ctx: MiddlewareContext[CompleteRequest],
        call_next: CallNext[CompleteRequest, CompleteResult],
    ) -> CompleteResult:
        return await call_next(ctx)

    async def on_initialized(
        self,
        ctx: MiddlewareContext[InitializedNotification],
        call_next: CallNext[InitializedNotification, None],
    ) -> None:
        return await call_next(ctx)

    async def on_roots_list_changed(
        self,
        ctx: MiddlewareContext[RootsListChangedNotification],
        call_next: CallNext[RootsListChangedNotification, None],
    ) -> None:
        return await call_next(ctx)

    async def on_progress(
        self,
        ctx: MiddlewareContext[ProgressNotification],
        call_next: CallNext[ProgressNotification, None],
    ) -> None:
        return await call_next(ctx)

    async def on_cancelled(
        self,
        ctx: MiddlewareContext[CancelledNotification],
        call_next: CallNext[CancelledNotification, None],
    ) -> None:
        return await call_next(ctx)
