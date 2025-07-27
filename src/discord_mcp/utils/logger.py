import datetime
import enum
import json
import logging
import os
import pathlib
import traceback
import typing as t
from logging.handlers import RotatingFileHandler

import pythonjsonlogger

__all__: tuple[str, ...] = (
    "LogLevelColors",
    "RelativePathFilter",
    "DailyRotatingFileHandler",
    "StructuredJsonFormatter",
    "setup_logging",
)


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


class StructuredJsonFormatter(pythonjsonlogger.json.JsonFormatter):
    """Custom formatter for log messages."""

    def __init__(
        self,
        *args: t.Any,
        fmt: str = "%(asctime)s %(name)s %(pathname)s %(funcName)s %(lineno)s %(levelname)s %(message)s",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        style: str = "%",
        json_default: t.Callable[..., t.Any] | str | None = None,
        json_encoder: t.Callable[..., t.Any] | str | None = None,
        json_serializer: t.Callable[..., t.Any] | str = json.dumps,
        json_indent: int | str | None = 2,
        json_ensure_ascii: bool = True,
        use_colors: bool = True,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(
            *args,
            **kwargs,
            fmt=fmt,
            datefmt=datefmt,
            style=style,
            json_default=json_default,
            json_encoder=json_encoder,
            json_serializer=json_serializer,
            json_indent=json_indent,
            json_ensure_ascii=json_ensure_ascii,
        )
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        record.levelname = f"{LogLevelColors.from_level(record.levelname)}{record.levelname}{LogLevelColors.ENDC}"
        formatted = super().format(record)
        if self.use_colors:
            return formatted.replace("\\u001b", "\033").replace("\u001b", "\033")
        return formatted

    def add_fields(
        self, log_record: t.Dict[str, t.Any], record: logging.LogRecord, message_dict: t.Dict[str, t.Any]
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            log_record["exception"] = {
                "exc_type": getattr(exc_type, "__name__", str(exc_type)),
                "exc_value": str(exc_value),
                "traceback": traceback.format_exception(exc_type, exc_value, exc_traceback),
            }
            log_record.pop("exc_info", None)
            log_record.pop("exc_text", None)


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
        self.setFormatter(StructuredJsonFormatter(use_colors=False))
        self.addFilter(RelativePathFilter())

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
    package_name: str = __name__.split(".")[0],
    level: int = logging.DEBUG,
    file_logging: bool = False,
    filename: str = "discord-mcp",
    log_dir: str | pathlib.Path = "logs",
) -> None:
    """
    Setup logging configuration for the entire application.

    Parameters
    ----------
    level : int
        The logging level to use.
    file_logging : bool
        Whether to enable file logging.
    filename : str
        The base filename for log files if file logging is enabled.
    log_dir : str
        The directory where log files will be stored.
    """
    # Get the root logger
    root_logger = logging.getLogger(package_name)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Set the level
    root_logger.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.addFilter(RelativePathFilter())
    console_handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(console_handler)

    # Create file handler if requested
    if file_logging:
        file_handler = DailyRotatingFileHandler(filename=filename, folder=log_dir)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "relative_path": {"()": RelativePathFilter},
    },
    "formatters": {
        "json_colored": {"()": StructuredJsonFormatter, "use_colors": True},
        "json_plain": {"()": StructuredJsonFormatter, "use_colors": False},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "json_colored",
            "filters": ["relative_path"],
            "stream": "ext://sys.stdout",
        },
        "file": {
            "()": DailyRotatingFileHandler,
            "level": "DEBUG",
            "formatter": "json_plain",
            "filename": "discord-mcp",
            "folder": "logs",
        },
    },
    "loggers": {
        "": {"handlers": ["console", "file"], "level": "DEBUG", "propagate": False},
        "discord": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
    },
}


def setup_all_logging():
    import logging.config

    logging.config.dictConfig(LOGGING_CONFIG)
