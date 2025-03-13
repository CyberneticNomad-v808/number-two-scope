# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# Name:         fastapi_logger
# Purpose:      Logging utilities for FastAPI implementation
#
# Author:       Agostino Panico <van1sh@van1shland.io>
#
# Created:      01/03/2025
# Copyright:    (c) poppopjmp
# License:      MIT
# -----------------------------------------------------------------
"""
SpiderFoot FastAPI Logger - Legacy Module

This is a legacy module that redirects to the new modular implementation.
It's kept for backward compatibility.
"""

from spiderfoot.fastapi.utils.logging import (
    setup_logging,
    get_logger,
    LoggingMiddleware,
    JSONLogFormatter
)
import warnings

# Show a deprecation warning
warnings.warn(
    "The spiderfoot.fastapi_logger module is deprecated. "
    "Please use spiderfoot.fastapi.utils.logging module instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from the new module structure
__all__ = ["setup_logging", "get_logger",
           "LoggingMiddleware", "JSONLogFormatter"]
