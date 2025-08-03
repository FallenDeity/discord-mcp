import enum

from pydantic import BaseModel


class ErrorCodes(enum.IntEnum):
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    RESOURCE_NOT_FOUND = -32001
    RESOURCE_READ_ERROR = -32002
    PROMPT_NOT_FOUND = -32003
    PROMPT_RENDER_ERROR = -32004
    DISABLED = -32005
    RATE_LIMIT_EXCEEDED = -32006
    PERMISSION_DENIED = -32007
    CHECK_FAILURE = -32008


class MiddlewareEventTypes(enum.StrEnum):
    REQUEST = "request"
    NOTIFICATION = "notification"


class MiddlewareRequestMethods(enum.StrEnum):
    CALL_TOOL = "tools/call"
    READ_RESOURCE = "resources/read"
    GET_PROMPT = "prompts/get"
    LIST_TOOLS = "tools/list"
    LIST_RESOURCES = "resources/list"
    LIST_RESOURCE_TEMPLATES = "resources/templates/list"
    LIST_PROMPTS = "prompts/list"
    INITIALIZE = "initialize"
    PING = "ping"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"
    SET_LEVEL = "logging/setLevel"
    COMPLETE = "completion/complete"


class MiddlewareNotificationMethods(enum.StrEnum):
    INITIALIZED = "notifications/initialized"
    ROOTS_LIST_CHANGED = "notifications/roots/list_changed"
    PROGRESS = "notifications/progress"
    CANCELLED = "notifications/cancelled"


class ServerType(enum.StrEnum):
    """Enum for server types."""

    STDIO = "stdio"
    HTTP = "http"


class ResourceReturnType(enum.Enum):
    """Enum to represent return types for resources.

    Used to automatically infer the ``mime_type``.
    """

    STR = str
    BYTES = bytes
    LIST = list
    DICT = dict
    NONE = None
    PYDANTIC_BASE_MODEL = BaseModel
