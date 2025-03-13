"""Logger configuration for SpiderFoot."""

from typing import Dict, Any, Optional, List
import logging
import logging.handlers
import os
import pathlib
import sys
import traceback
from logging import (
    DEBUG,
    INFO,
    FileHandler,
    Formatter,
)


# Import helpers dynamically to avoid circular imports
def get_helpers():
    """Get helpers module to avoid circular imports."""
    from spiderfoot.helpers import SpiderFootHelpers

    return SpiderFootHelpers


def get_log_paths():
    """Get log file paths.

    Returns:
        dict: paths to log files
    """
    helpers = get_helpers()
    log_dir = helpers.logPath()
    paths = {
        "debug": f"{log_dir}/spiderfoot.debug.log",
        "error": f"{log_dir}/spiderfoot.error.log",
        "syslog": f"{log_dir}/spiderfoot.syslog.log",
    }
    return paths


# Store module loggers to avoid creating duplicates
_module_loggers: Dict[str, logging.Logger] = {}

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configure_root_logger(debug: bool = False, log_file: str = None) -> None:
    """Configure the root logger with basic settings.

    This sets up minimal console logging for the root logger.
    Modules should generally use their own named loggers.

    Args:
        debug: Whether to enable debug logging
        log_file: Optional path to log file
    """
    level = logging.DEBUG if debug else logging.INFO

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicate logging
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create and add console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
            file_handler.setLevel(level)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to create log file handler: {e}")


def get_module_logger(module_name: str) -> logging.Logger:
    """Get or create a logger for the specified module.

    This function ensures that each module gets its own logger with consistent
    configuration. Loggers are cached to avoid creating duplicates.

    Args:
        module_name: The name of the module requesting a logger

    Returns:
        logging.Logger: Configured logger for the module
    """
    if module_name in _module_loggers:
        return _module_loggers[module_name]

    # Create a new logger for this module
    logger = logging.getLogger(f"spiderfoot.{module_name}")

    # Cache the logger for future use
    _module_loggers[module_name] = logger

    return logger


def setup_file_logging(log_file: str, level: int = logging.INFO) -> None:
    """Set up logging to a file.

    Args:
        log_file: Path to log file
        level: Log level (default: INFO)
    """
    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Create file handler
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
        handler.setLevel(level)

        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        # Log the setup
        root_logger.debug(f"Logging to file: {log_file}")
    except Exception as e:
        print(f"Failed to set up file logging: {e}")


def get_log_level_from_config(config: Optional[Dict[str, Any]] = None) -> int:
    """Determine the appropriate log level from configuration.

    Args:
        config: SpiderFoot configuration dictionary

    Returns:
        int: The logging level (from logging module constants)
    """
    if config is None:
        return logging.INFO

    if config.get("_debug", False):
        return logging.DEBUG

    return logging.INFO


def setup_scan_logger(scan_id: str) -> logging.Logger:
    """Set up a logger for a specific scan.

    Args:
        scan_id: The scan ID

    Returns:
        logging.Logger: Logger for the scan
    """
    logger = logging.getLogger(f"spiderfoot.scan.{scan_id}")

    # Set up a file handler for this scan
    log_dir = get_helpers().logPath()
    scan_log_file = os.path.join(log_dir, f"scan_{scan_id}.log")

    try:
        handler = logging.FileHandler(scan_log_file)
        handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    except Exception as e:
        print(f"Failed to set up scan logger: {e}")

    return logger
