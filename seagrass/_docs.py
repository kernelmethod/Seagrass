# This module primarily exists for the purposes of helping generate the
# Seagrass documentation. The code in this module is not part of the
# public Seagrass API.

import logging
import logging.config
import sys
from pythonjsonlogger import jsonlogger     # type: ignore
from seagrass import DEFAULT_LOGGER_NAME


class LogFormatter(jsonlogger.JsonFormatter):   # type: ignore
    def add_fields(self, log_record, record, message_dict):
        super(LogFormatter, self).add_fields(log_record, record, message_dict)
        log_record["level"] = record.levelname


def configure_logging(name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
    """Set up the default logging configuration for the documentation."""

    logger = logging.getLogger(name)
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = LogFormatter()
    handler.setFormatter(formatter)

    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger
