import enum

from pydantic import BaseModel


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


class DiscordMCPFunctionType(enum.IntEnum):
    TOOL = enum.auto()
    RESOURCE = enum.auto()
    PROMPT = enum.auto()
