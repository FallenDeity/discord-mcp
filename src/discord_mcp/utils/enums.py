import enum
from inspect import _empty


class ServerType(enum.StrEnum):
    """Enum for server types."""

    STDIO = "stdio"
    HTTP = "http"


class ResourceReturnType(enum.Enum):
    STR = str
    BYTES = bytes
    LIST = list
    DICT = dict
    NONE = None
    EMPTY = _empty
