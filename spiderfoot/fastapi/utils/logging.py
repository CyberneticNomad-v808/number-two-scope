import logging
from typing import Dict, Any


def setup_logging(config: Dict[str, Any] = None) -> None:
    """Configure logging for the FastAPI application.

    Args:
        config: Dictionary containing logging configuration
    """
    if config is None:
        config = {}

    log_level = config.get("log_level", "INFO")

    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Name for the logger

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)
