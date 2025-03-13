# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# Name:         fastapi_error_handlers
# Purpose:      Error handling utilities for FastAPI implementation
#
# Author:       Agostino Panico <van1sh@van1shland.io>
#
# Created:      01/03/2025
# Copyright:    (c) poppopjmp
# License:      MIT
# -----------------------------------------------------------------
"""
SpiderFoot FastAPI Error Handlers - Legacy Module

This is a legacy module that redirects to the new modular implementation.
It's kept for backward compatibility.
"""

from spiderfoot.fastapi.utils.errors import (
    setup_error_handlers,
    ErrorDetail
)
import warnings

# Show a deprecation warning
warnings.warn(
    "The spiderfoot.fastapi_error_handlers module is deprecated. "
    "Please use spiderfoot.fastapi.utils.errors module instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from the new module structure

__all__ = ["setup_error_handlers", "ErrorDetail"]
