# This module primarily exists for the purposes of helping generate the
# Seagrass documentation. The code in this module is not part of the
# public Seagrass API.

import logging
import logging.config
from seagrass import DEFAULT_LOGGER_NAME


def configure_logging(name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
    """Set up the default logging configuration for the documentation."""

    logger = logging.getLogger(name)
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "(%(levelname)s) %(name)s: %(message)s",
            },
        },
        "handlers": {
            "default": {
                "level": "DEBUG",
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            DEFAULT_LOGGER_NAME: {
                "handlers": ["default"],
                "level": "DEBUG",
                "propagate": False,
            },
        }
    })

    return logging.getLogger(DEFAULT_LOGGER_NAME)
