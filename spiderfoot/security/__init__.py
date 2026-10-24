# SpiderFoot Security Module
# Enhanced security features for SpiderFoot web interface

from .csrf_middleware import CSRFMiddleware

__all__ = ['CSRFMiddleware']
