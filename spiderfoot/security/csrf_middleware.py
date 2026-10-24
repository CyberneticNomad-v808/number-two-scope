# -*- coding: utf-8 -*-
"""
CSRF Protection Middleware for SpiderFoot

This module provides CSRF protection that can be configured to be permissive
for development environments while logging security warnings.
"""

import logging
import os
import cherrypy


class CSRFMiddleware:
    """
    CSRF Protection middleware that can be configured for development use.

    In development mode (single user, protected LAN), CSRF validation failures
    are logged as warnings but don't block requests to maintain functionality.
    """

    def __init__(self, config=None):
        self.log = logging.getLogger(__name__)
        self.config = config or {}

        # Check if CSRF is enabled via config or environment
        self.enabled = self.config.get('_csrf_enabled', False)

        # Check development mode from config or environment
        env_dev_mode = os.environ.get('SF_DEVELOPMENT_MODE', 'false').lower() == 'true'
        self.development_mode = self.config.get('_csrf_development_mode', env_dev_mode)

        if self.enabled:
            self.log.info(f"CSRF protection initialized (development_mode={self.development_mode})")

    def __call__(self):
        """CherryPy tool hook for CSRF protection."""
        if not self.enabled:
            return

        if cherrypy.request.method.upper() in ('POST', 'PUT', 'DELETE', 'PATCH'):
            self._check_csrf_token()

    def _check_csrf_token(self):
        """Check CSRF token for state-changing requests."""
        # Get token from header or form data
        csrf_token = cherrypy.request.headers.get('X-CSRF-Token')

        if not csrf_token and hasattr(cherrypy.request, 'params'):
            csrf_token = cherrypy.request.params.get('csrf_token')

        if not csrf_token:
            self._handle_csrf_failure("CSRF token missing")
            return

        # In a full implementation, validate the token here
        # For now, we just check if it exists
        if not self._validate_token(csrf_token):
            self._handle_csrf_failure("Invalid CSRF token")
            return

    def _validate_token(self, token):
        """
        Validate CSRF token.
        This is a simplified implementation - in production you'd want
        proper token generation and validation.
        """
        # For development, just check token exists
        return bool(token)

    def _handle_csrf_failure(self, reason):
        """Handle CSRF validation failure."""
        client_ip = cherrypy.request.headers.get('X-Forwarded-For',
                                                 cherrypy.request.headers.get('X-Real-IP',
                                                                             cherrypy.request.remote.ip))

        # Log the security warning
        self.log.warning(f"CSRF validation failed: {reason} from IP {client_ip} for {cherrypy.request.path_info}")

        if self.development_mode:
            # In development mode, log but allow the request to continue
            self.log.info("Development mode: allowing request despite CSRF failure")
        else:
            # In production mode, block the request
            raise cherrypy.HTTPError(403, f"CSRF validation failed: {reason}")


def create_csrf_tool(config):
    """
    Create a CherryPy CSRF tool with the given configuration.

    Args:
        config: SpiderFoot configuration dictionary

    Returns:
        CherryPy Tool instance
    """
    csrf_middleware = CSRFMiddleware(config)
    return cherrypy.Tool('before_handler', csrf_middleware, priority=50)


def enable_csrf_protection(config=None):
    """
    Enable CSRF protection for the web server.

    Args:
        config: SpiderFoot configuration dictionary (optional)
    """
    config = config or {}

    # Register the CSRF tool
    csrf_tool = create_csrf_tool(config)
    cherrypy.tools.csrf_protection = csrf_tool

    # Enable it in the configuration
    cherrypy.config.update({
        'tools.csrf_protection.on': True
    })
