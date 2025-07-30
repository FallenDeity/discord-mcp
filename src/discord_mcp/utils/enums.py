import enum

from pydantic import BaseModel


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
