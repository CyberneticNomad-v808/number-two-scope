# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# Name:         cherrypy_compat
# Purpose:      Compatibility layer to help transition from CherryPy to FastAPI
#
# Author:   Agostino Panico <van1sh@van1shland.io>
#
# Created:  01/03/2025
# Copyright:  (c) poppopjmp
# License:      MIT
# -----------------------------------------------------------------
"""This module provides compatibility shims to help transition from CherryPy to
FastAPI.

It provides mock classes and functions that mimic CherryPy's behavior
but delegate to FastAPI.
"""

import sys
import warnings

# Warn about using compatibility layer
warnings.warn(
    "Using CherryPy compatibility layer. Please update your code to use FastAPI directly.",
    DeprecationWarning,
    stacklevel=2
)

# Mock CherryPy classes and functions
class _MockCherryPy:
    """Mock CherryPy module for compatibility."""
    
    class _MockResponse:
        """Mock CherryPy response object."""
        def __init__(self):
            self.headers = {}
            self.status = 200
            self.body = None
    
    class _MockRequest:
        """Mock CherryPy request object."""
        def __init__(self):
            self.headers = {}
            self.params = {}
    
    class _MockError:
        """Mock CherryPy error handling."""
        def get_error_page(self, status, traceback=None):
            """Get error page HTML."""
            return f"<html><body>Error {status}<pre>{traceback}</pre></body></html>".encode()
        
        def format_exc(self):
            """Format exception traceback."""
            import traceback
            return traceback.format_exc()
    
    # Mock response and request
    response = _MockResponse()
    request = _MockRequest()
    _cperror = _MockError()

    # Mock decorators
    class expose:
        """Mock CherryPy expose decorator."""
        def __init__(self, *args, **kwargs):
            pass
        
        def __call__(self, func):
            func._cp_expose = True
            return func
    
    class tools:
        """Mock CherryPy tools module."""
        class json_out:
            """Mock CherryPy JSON output tool."""
            def __init__(self, *args, **kwargs):
                pass
            
            def __call__(self, func):
                func._cp_json_out = True
                return func

    # Mock CherryPy.HTTPRedirect
    class HTTPRedirect(Exception):
        """Mock CherryPy HTTP redirect."""
        def __init__(self, url, status=303):
            self.urls = [url]
            self.status = status
            super().__init__(url)

# Create a mock CherryPy module in sys.modules
sys.modules['cherrypy'] = _MockCherryPy()
