"""SpiderFoot logging functionality.

This module provides logging capabilities for SpiderFoot, including:
- Thread-safe logging implementation
- Logging to console, files, and SQLite database
- Centralized logging system using a queue-based approach
- Support for multiple log formats and destinations
"""

import warnings

# Import all functionality from the new modular structure
from spiderfoot.fastapi.utils.logging import (
    SafeQueueListener,
    SpiderFootSqliteLogHandler,
    SpiderFootLogger,
    logListenerSetup,
    logWorkerSetup,
    stop_listener,
    logEvent,
    get_logger,
    setup_logging
)

# Show a deprecation warning
warnings.warn(
    "The spiderfoot.logger module is deprecated. "
    "Please use spiderfoot.fastapi.utils.logging module instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all symbols from the new module
__all__ = [
    "SafeQueueListener",
    "SpiderFootSqliteLogHandler",
    "SpiderFootLogger",
    "logListenerSetup",
    "logWorkerSetup",
    "stop_listener",
    "logEvent",
    "get_logger",
    "setup_logging"
]
