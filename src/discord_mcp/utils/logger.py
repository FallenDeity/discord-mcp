import contextlib
import contextvars
import datetime
import enum
import json
import logging
import logging.config
import os
import pathlib
import traceback
import typing as t
from logging.handlers import RotatingFileHandler

__all__: tuple[str, ...] = (
    "LogLevelColors",
    "RelativePathFilter",
    "DailyRotatingFileHandler",
    "JSONFormatter",
    "setup_logging",
    "add_to_log_context",
)

_request_context: contextvars.ContextVar[dict[str, t.Any]] = contextvars.ContextVar("request_context", default={})


class LogLevelColors(enum.StrEnum):
    """Colors for the log levels."""

    DEBUG = "\033[96m"
    INFO = "\033[92m"
    WARNING = "\033[93m"
    ERROR = "\033[33m"
    CRITICAL = "\033[91m"
    ENDC = "\033[0m"

    @classmethod
    def from_level(cls, level: str) -> str:
        return getattr(cls, level.upper(), cls.ENDC)


class RelativePathFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.pathname = record.pathname.replace(os.getcwd(), "~")
        return True


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = _request_context.get()
        for key, value in context.items():
            setattr(record, key, value)
        return True


BASE_DICT_ATTRS: tuple[str, ...] = (
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
)


def pass_args(args: list[t.Any], msg: str) -> str:
    msg = str(msg)
    if args:
        msg = msg % args
    return msg


class JSONFormatter(logging.Formatter):
    def __init__(
        self,
        *,
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        use_colors: bool = True,
    ) -> None:
        super().__init__("%(levelname)s %(name)s %(message)s", datefmt=datefmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        json_log: dict[str, t.Any] = {
            "asctime": self.formatTime(record, self.datefmt),
            "levelname": (
                record.levelname
                if not self.use_colors
                else f"{LogLevelColors.from_level(record.levelname)}{record.levelname}{LogLevelColors.ENDC}"
            ),
            "name": f"{record.name}",
            "logLocation": f"{record.name}.{record.funcName}:{record.lineno}",
            "message": record.getMessage(),
        }
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            json_log["exception"] = {
                "exc_type": getattr(exc_type, "__name__", str(exc_type)),
                "exc_value": str(exc_value),
                "traceback": traceback.format_exception(exc_type, exc_value, exc_traceback),
            }

        for attr in record.__dict__:
            if attr not in BASE_DICT_ATTRS:
                # this is needed because uvicorn passes some extra colored messages
                # we can use this too ig
                if attr == "color_message" and self.use_colors:
                    json_log[attr] = pass_args(record.args, getattr(record, attr))  # type: ignore
                elif attr == "color_message" and not self.use_colors:
                    pass  # not add color_message if colors are disabled (reduces redundancy in logs)
                else:
                    json_log[attr] = getattr(record, attr)

        formatted = json.dumps(json_log, indent=4)
        return formatted.replace("\\u001b", "\033").replace("\u001b", "\033")


class DailyRotatingFileHandler(RotatingFileHandler):
    """A file handler that writes log messages to a file."""

    def __init__(
        self,
        filename: str | os.PathLike[str],
        mode: str = "a",
        maxBytes: int = 10 * 1024 * 1024,
        backupCount: int = 5,
        encoding: str | None = "utf-8",
        delay: bool = False,
        errors: str | None = None,
        *,
        folder: pathlib.Path | str = "logs",
    ) -> None:
        self._last_entry = datetime.datetime.today()
        self.folder = pathlib.Path(folder)
        self.filename = filename
        self.folder.mkdir(exist_ok=True)
        super().__init__(
            self.folder / f"{datetime.datetime.today().strftime('%Y-%m-%d')}-{self.filename}.log",
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            errors=errors,
        )
        self.setFormatter(JSONFormatter(use_colors=False))
        self.addFilter(RelativePathFilter())
        self.addFilter(ContextFilter())

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record."""
        if self._last_entry.date() != datetime.datetime.today().date():
            self._last_entry = datetime.datetime.today()
            self.close()
            self.baseFilename = (
                self.folder / f"{self._last_entry.strftime('%Y-%m-%d')}-{self.filename}.log"
            ).as_posix()
            self.stream = self._open()
        super().emit(record)


def setup_logging(
    log_level: int = logging.DEBUG,
    file_logging: bool = True,
    filename: str = "discord-mcp",
    log_dir: str | pathlib.Path = "logs",
) -> None:
    """
    Set up structured logging for console and file handlers.
    """
    handlers: dict[str, dict[str, t.Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "json_colored",
            "filters": ["relative_path", "context_filter"],
            "stream": "ext://sys.stderr",
        },
    }

    if file_logging:
        handlers["file"] = {
            "()": DailyRotatingFileHandler,
            "level": log_level,
            "formatter": "json_plain",
            "filename": filename,
            "folder": str(log_dir),
        }

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "relative_path": {
                "()": RelativePathFilter,
            },
            "context_filter": {
                "()": ContextFilter,
            },
        },
        "formatters": {
            "json_colored": {
                "()": JSONFormatter,
                "use_colors": True,
            },
            "json_plain": {
                "()": JSONFormatter,
                "use_colors": False,
            },
        },
        "handlers": handlers,
        "loggers": {
            "": {
                "handlers": list(handlers.keys()),
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": list(handlers.keys()),
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": list(handlers.keys()),
                "level": "INFO",
                "propagate": False,
            },
            "discord": {
                "handlers": list(handlers.keys()),
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)


@contextlib.contextmanager
def add_to_log_context(**kwargs: t.Any) -> t.Iterator[None]:
    current_context = _request_context.get()
    new_context = {**current_context, **kwargs}

    # Set the new context and get the token for restoration
    token = _request_context.set(new_context)

    try:
        yield
    finally:
        _request_context.reset(token)
