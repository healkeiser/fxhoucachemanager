"""Logging configuration for the application."""

# Built-in
from datetime import datetime
import logging
from logging.handlers import TimedRotatingFileHandler

# Internal
from fxhoucachemanager import fxenvironment


# Global list to keep track of all loggers
loggers = []


def configure_logger(name: str) -> logging.Logger:
    """Configure and return a logger.

    Args:
        name (str): The name of the logger. Typically the name of the module.

    Returns:
        The configured logger.
    """
    global loggers

    # Create the logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Check if the logger already has handlers to avoid duplicate logs
    if not logger.handlers:

        # Create a rotating file handler with date in the filename
        current_date = datetime.now().strftime("%Y_%m_%d")
        log_file_with_date = (
            fxenvironment.FXCACHEMANAGER_LOG_DIR
            / f"fxcachemanager_{current_date}.log"
        )
        file_handler = TimedRotatingFileHandler(
            log_file_with_date,
            when="midnight",
            interval=1,
            backupCount=7,
            utc=True,
        )
        file_handler.suffix = "%Y-%m-%d"
        stream_handler = logging.StreamHandler()

        # Format
        width_name = 20
        width_levelname = 8
        log_fmt = (
            f"{{asctime}} | {{name:^{width_name}s}} | "
            f"{{lineno}} | "
            f"{{levelname:>{width_levelname}s}} | {{message}}"
        )

        # Create formatters and add them to the handlers
        formatter = logging.Formatter(log_fmt, style="{", datefmt="%H:%M:%S")
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    # Add the logger to the global list
    loggers.append(logger)

    return logger


def set_log_level(level: int) -> None:
    """Set the log level for all loggers configured by this application.

    Args:
        level (int): The log level to set (e.g., logging.DEBUG, logging.INFO).
    """

    global loggers
    for logger in loggers:
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)
