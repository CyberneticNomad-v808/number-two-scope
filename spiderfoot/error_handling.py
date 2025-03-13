"""
SpiderFoot error handling module.

This module provides utilities for consistent error handling across the application.
It centralizes error handling patterns and integrates with the logging system.
"""

import sys
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union

from spiderfoot.logconfig import get_module_logger


class SpiderFootError(Exception):
    """Base exception class for all SpiderFoot errors."""
    pass


class SpiderFootDatabaseError(SpiderFootError):
    """Exception raised for database errors."""
    pass


class SpiderFootScanError(SpiderFootError):
    """Exception raised for scan errors."""
    pass


class SpiderFootConfigError(SpiderFootError):
    """Exception raised for configuration errors."""
    pass


class SpiderFootAPIError(SpiderFootError):
    """Exception raised for API errors."""
    pass


def handle_exception(exception: Exception, module_name: str, fatal: bool = False) -> None:
    """Handle an exception with appropriate logging.

    Args:
        exception: The exception to handle
        module_name: Module name for logging
        fatal: Whether the exception should cause the application to exit
    """
    logger = get_module_logger(module_name)
    
    error_message = str(exception)
    error_type = exception.__class__.__name__
    
    if fatal:
        logger.critical(f"FATAL ERROR ({error_type}): {error_message}", exc_info=True)
        sys.exit(1)
    else:
        logger.error(f"ERROR ({error_type}): {error_message}", exc_info=True)


def error_handler(func: Callable) -> Callable:
    """Decorator for handling errors in functions.

    Args:
        func: Function to decorate

    Returns:
        Callable: Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        module_name = func.__module__.split('.')[-1]
        try:
            return func(*args, **kwargs)
        except Exception as e:
            handle_exception(e, module_name)
            raise
    return wrapper


def api_error_handler(func: Callable) -> Callable:
    """Decorator for handling errors in API endpoints.

    Args:
        func: Function to decorate

    Returns:
        Callable: Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        module_name = func.__module__.split('.')[-1]
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = get_module_logger(module_name)
            logger.error(f"API Error in {func.__name__}: {str(e)}", exc_info=True)
            return {"error": str(e), "status": "error"}
    return wrapper


def database_error_handler(func: Callable) -> Callable:
    """Decorator for handling database errors.

    Args:
        func: Function to decorate

    Returns:
        Callable: Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        module_name = func.__module__.split('.')[-1]
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = get_module_logger(module_name)
            logger.error(f"Database Error in {func.__name__}: {str(e)}", exc_info=True)
            raise SpiderFootDatabaseError(f"Database operation failed: {str(e)}")
    return wrapper


def get_error_context() -> str:
    """Get context information about the current exception.

    Returns:
        str: Formatted error context
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if not all([exc_type, exc_value, exc_traceback]):
        return "No exception information available"
    
    tb_entries = traceback.extract_tb(exc_traceback)
    
    # Format the traceback
    context = f"Exception Type: {exc_type.__name__}\n"
    context += f"Exception Value: {exc_value}\n"
    context += "Traceback:\n"
    
    for tb in tb_entries:
        filename = tb.filename
        line = tb.lineno
        function = tb.name
        context += f"  File '{filename}', line {line}, in {function}\n"
    
    return context
