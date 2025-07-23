import logging

logger = logging.getLogger(__name__)


def foo():
    logger.info("This is an info message from foo.")
    logger.debug("This is a debug message from foo.")
    logger.warning("This is a warning message from foo.")
