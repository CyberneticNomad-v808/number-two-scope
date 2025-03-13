# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# Name:         fastapi_utils
# Purpose:      Utility functions for FastAPI implementation
#
# Author:       Agostino Panico <van1sh@van1shland.io>
#
# Created:      01/03/2025
# Copyright:    (c) poppopjmp
# License:      MIT
# -----------------------------------------------------------------
"""
SpiderFoot FastAPI Utilities - Legacy Module

This is a legacy module that redirects to the new modular implementation.
It's kept for backward compatibility.
"""

import warnings

# Show a deprecation warning
warnings.warn(
    "The spiderfoot.fastapi_utils module is deprecated. "
    "Please use spiderfoot.fastapi.utils modules instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from the new module structure
from spiderfoot.fastapi.utils.security import (
    generate_api_key,
    setup_cors,
    APIKeyAuth
)

__all__ = ["generate_api_key", "setup_cors", "APIKeyAuth"]
