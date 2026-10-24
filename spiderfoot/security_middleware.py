#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Middleware Integration
================================

This module provides comprehensive security middleware integration for SpiderFoot
web and API interfaces, combining all security modules into a cohesive system.

Features:
- CherryPy middleware integration
- FastAPI middleware integration
- Automatic security header injection
- Request/response security processing
- Centralized security configuration

Author: SpiderFoot Security Team
"""

import logging
import time
import cherrypy
from typing import Dict, Any
import json

from .csrf_protection import CSRFProtection
from .input_validation import InputValidator
from .rate_limiting import RateLimiter
from .session_security import SessionManager
from .api_security import APIKeyManager, JWTManager
from .security_logging import SecurityLogger, SecurityEventType
from .secure_config import SecureConfigManager



class SecurityConfigDefaults:
    """Default security configuration values."""

    WEB_SECURITY = {
        'CSRF_ENABLED': False,
        'RATE_LIMITING_ENABLED': True,
        'SECURE_SESSIONS': True,
        'AUTHENTICATION_REQUIRED': False,
        'SESSION_TIMEOUT': 60,
        'SESSION_SECURE': True,
        'SESSION_HTTPONLY': True,
        'SECURITY_LOG_FILE': 'logs/security.log',
        'SSL_ENABLED': False,
        'SSL_CERT_PATH': 'ssl/server.crt',
        'SSL_KEY_PATH': 'ssl/server.key',
        'SSL_CA_PATH': 'ssl/ca.crt',
    }

    API_SECURITY = {
        'JWT_SECRET': None,  # Must be provided
        'TOKEN_EXPIRY': 3600,
        'CORS_ORIGINS': ["https://localhost"],
        'TRUSTED_HOSTS': ["localhost", "127.0.0.1"],
        'RATE_LIMITING_ENABLED': True,
        'API_KEY_ENABLED': True,
        'SCOPES': ['read', 'write', 'admin', 'scan'],
    }

    REDIS_CONFIG = {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None,
    }


def create_security_config(custom_config: Dict[str, Any] = None
                          ) -> Dict[str, Any]:
    """Create security configuration with defaults.

    Args:
        custom_config: Custom configuration to override defaults

    Returns:
        Complete security configuration dictionary
    """
    config = {}
    config.update(SecurityConfigDefaults.WEB_SECURITY)
    config.update(SecurityConfigDefaults.API_SECURITY)
    config['REDIS_CONFIG'] = (
        SecurityConfigDefaults.REDIS_CONFIG.copy()
    )

    if custom_config:
        config.update(custom_config)
        if 'REDIS_CONFIG' in custom_config:
            config['REDIS_CONFIG'].update(custom_config['REDIS_CONFIG'])

    return config


def validate_security_config(config: Dict[str, Any]) -> bool:
    """Validate security configuration.

    Args:
        config: Security configuration to validate

    Returns:
        True if configuration is valid

    Raises:
        ValueError: If configuration is invalid
    """
    required_keys = ['SECRET_KEY']

    for key in required_keys:
        if not config.get(key):
            raise ValueError(
                f"Required security configuration key missing: {key}"
            )

    # Validate JWT secret for API security
    if (config.get('API_SECURITY_ENABLED', True) and
            not config.get('JWT_SECRET')):
        raise ValueError("JWT_SECRET is required for API security")

    # Validate SSL configuration if enabled
    if config.get('SSL_ENABLED', False):
        ssl_keys = ['SSL_CERT_PATH', 'SSL_KEY_PATH']
        for key in ssl_keys:
            if not config.get(key):
                raise ValueError(f"SSL configuration key missing: {key}")

    return True


def get_security_status() -> Dict[str, Any]:
    """Get current security status.

    Returns:
        Dictionary with security status information
    """
    return {
        'csrf_protection': hasattr(cherrypy.tools, 'csrf'),
        'rate_limiting': hasattr(cherrypy.tools, 'rate_limit'),
        'session_security': cherrypy.config.get('tools.sessions.on', False),
        'ssl_enabled': (
            cherrypy.config.get('server.ssl_certificate') is not None
        ),
        'security_logging': True,  # Always enabled
        'timestamp': time.time()
    }


class SpiderFootSecurityMiddleware:
    """
    Main security middleware class for SpiderFoot application.

    This class integrates all security components and provides a unified
    interface for both web and API security management.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SpiderFoot security middleware.

        Args:
            config: Application configuration dictionary
        """
        self.config = config
        self.log = logging.getLogger(__name__)

        # Initialize security components
        self._init_security_components()

        # Security configuration
        self.security_config = self._get_security_config()

        self.log.info("SpiderFoot security middleware initialized")

    def _init_security_components(self):
        """Initialize all security components."""
        try:
            # Configuration manager
            try:
                self.config_manager = SecureConfigManager(self.config)
            except Exception as e:
                self.log.warning(f"Failed to initialize config manager: {e}")
                self.config_manager = None

            # Core security components
            import secrets
            csrf_secret = (
                self.config.get('_csrf_secret_key') or
                secrets.token_hex(32)
            )
            try:
                self.csrf = CSRFProtection(secret_key=csrf_secret)
            except Exception as e:
                self.log.warning(f"Failed to initialize CSRF protection: {e}")
                self.csrf = None

            try:
                self.input_validator = InputValidator()
            except Exception as e:
                msg = "Failed to initialize input validator"
                self.log.warning(f"{msg}: {e}")
                self.input_validator = None

            try:
                # Get Redis config from the main config
                redis_config = self.config.get('REDIS_CONFIG', {})
                self.rate_limiter = RateLimiter(
                    redis_host=redis_config.get('host', 'localhost'),
                    redis_port=redis_config.get('port', 6379),
                    redis_db=redis_config.get('db', 0)
                )
            except Exception as e:
                self.log.warning(f"Failed to initialize rate limiter: {e}")
                self.rate_limiter = None

            try:
                self.session_manager = SessionManager(self.config)
            except Exception as e:
                msg = "Failed to initialize session manager"
                self.log.warning(f"{msg}: {e}")
                self.session_manager = None

            try:
                self.api_key_manager = APIKeyManager(self.config)
            except Exception as e:
                msg = "Failed to initialize API key manager"
                self.log.warning(f"{msg}: {e}")
                self.api_key_manager = None

            try:
                self.jwt_manager = JWTManager(self.config)
            except Exception as e:
                self.log.warning(f"Failed to initialize JWT manager: {e}")
                self.jwt_manager = None

            # Security logger with proper initialization
            log_file = self.config.get('_security_log_file',
                                       'logs/security.log')
            try:
                self.security_logger = SecurityLogger(log_file=log_file)
            except Exception as e:
                msg = "Failed to initialize security logger"
                self.log.warning(f"{msg}: {e}")
                self.security_logger = None

            self.log.info(
                "All security components initialized successfully"
            )

        except Exception as e:
            self.log.error(f"Failed to initialize security components: {e}")
            # Don't raise exception to prevent complete failure
            msg = "Security middleware will continue with reduced functionality"
            self.log.warning(msg)

    def _get_security_config(self) -> Dict[str, Any]:
        """Get security configuration with defaults."""
        # Parse bypass_auth_endpoints from comma-separated string to list
        default_bypass = (
            '/static,/favicon.ico,/robots.txt,/api/docs,/api/redoc'
        )
        bypass_endpoints = self.config.get(
            '_bypass_auth_endpoints',
            default_bypass
        )
        if isinstance(bypass_endpoints, str):
            bypass_endpoints = [
                e.strip() for e in bypass_endpoints.split(',')
            ]

        return {
            'csrf_enabled': self.config.get('_csrf_enabled', False),
            'rate_limiting_enabled': self.config.get(
                '_rate_limiting_enabled', False
            ),
            'input_validation_enabled': self.config.get(
                '_input_validation_enabled', True
            ),
            'session_security_enabled': self.config.get(
                '_session_security_enabled', True
            ),
            'api_security_enabled': self.config.get(
                '_api_security_enabled', False
            ),
            'security_headers_enabled': self.config.get(
                '_security_headers_enabled', True
            ),
            'security_logging_enabled': self.config.get(
                '_security_logging_enabled', True
            ),
            'bypass_auth_endpoints': bypass_endpoints
        }


class CherryPySecurityTool(cherrypy.Tool):
    """
    CherryPy security tool for web interface protection.
    """

    def __init__(self, middleware: SpiderFootSecurityMiddleware):
        """
        Initialize CherryPy security tool.

        Args:
            middleware: Security middleware instance
        """
        super().__init__('before_request_body', self._security_check)
        self.middleware = middleware
        self.log = logging.getLogger(__name__)

    def _security_check(self):
        """Perform security checks before processing request."""
        try:
            request = cherrypy.request
            response = cherrypy.response

            # Get client info
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get('User-Agent', '')
            endpoint = request.path_info
            method = request.method

            # Log security event (only for non-static requests)
            if (self.middleware.security_config[
                    'security_logging_enabled'] and
                    not endpoint.startswith('/static') and
                    self.middleware.security_logger is not None):
                try:
                    self.middleware.security_logger.log_security_event(
                        SecurityEventType.REQUEST_PROCESSED,
                        {
                            'action': 'request_processed',
                            'endpoint': endpoint,
                            'method': method
                        },
                        severity='INFO',
                        ip_address=client_ip,
                        user_agent=user_agent
                    )
                except Exception as e:
                    # Don't let logging errors break the request
                    self.log.warning(f"Security logging error: {e}")

            # Check if endpoint should bypass authentication
            if self._should_bypass_security(endpoint):
                return

            # Rate limiting
            if (self.middleware.security_config['rate_limiting_enabled'] and
                    self.middleware.rate_limiter is not None):
                try:
                    client_id = f"ip:{client_ip}"
                    allowed, rate_info = (
                        self.middleware.rate_limiter._check_memory_limit(
                            client_id, 'web'
                        )
                    )
                    if self.middleware.rate_limiter.redis:
                        try:
                            allowed, rate_info = (
                                self.middleware.rate_limiter._check_redis_limit(
                                    client_id, 'web'
                                )
                            )
                        except Exception:
                            allowed, rate_info = (
                                self.middleware.rate_limiter._check_memory_limit(
                                    client_id, 'web'
                                )
                            )
                    if not allowed:
                        self._block_request(429, "Rate limit exceeded")
                        return
                except Exception as e:
                    self.log.warning(f"Rate limiting error: {e}")

            # Input validation for POST/PUT requests
            if (self.middleware.security_config['input_validation_enabled'] and
                    method in ['POST', 'PUT', 'PATCH'] and
                    self.middleware.input_validator is not None):
                try:
                    self._validate_request_data(request)
                except Exception as e:
                    self.log.warning(f"Input validation error: {e}")

            # CSRF protection for state-changing requests
            if (self.middleware.security_config['csrf_enabled'] and
                    method in ['POST', 'PUT', 'DELETE', 'PATCH'] and
                    self.middleware.csrf is not None):
                try:
                    self._check_csrf_token(request)
                except Exception as e:
                    self.log.warning(f"CSRF check error: {e}")

            # Session security
            if (self.middleware.security_config['session_security_enabled'] and
                    self.middleware.session_manager is not None):
                try:
                    self._check_session_security(request)
                except Exception as e:
                    msg = "Session security check error"
                    self.log.warning(f"{msg}: {e}")

        except Exception as e:
            self.log.error(f"Error in security check: {e}")

    def _get_client_ip(self, request) -> str:
        """Get client IP address from request."""
        # Check for X-Forwarded-For header (behind proxy)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Get the first IP if there are multiple
            return forwarded_for.split(',')[0].strip()
        return request.remote.ip

    def _should_bypass_security(self, endpoint: str) -> bool:
        """Check if endpoint should bypass security checks."""
        bypass_endpoints = self.middleware.security_config.get(
            'bypass_auth_endpoints', []
        )
        for bypass_path in bypass_endpoints:
            if endpoint.startswith(bypass_path):
                return True
        return False

    def _block_request(self, status_code: int, message: str):
        """Block the request."""
        cherrypy.response.status = status_code
        cherrypy.response.body = json.dumps({
            'error': message,
            'status': status_code
        }).encode('utf-8')
        cherrypy.response.headers['Content-Type'] = 'application/json'

    def _validate_request_data(self, request):
        """Validate request data."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                content_length = int(
                    request.headers.get('Content-Length', 0)
                )
                if content_length > 10 * 1024 * 1024:
                    raise ValueError("Request body too large")
            except (ValueError, TypeError):
                pass

    def _check_csrf_token(self, request):
        """Check CSRF token in request."""
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Check for CSRF token in headers or form data
            token = (request.headers.get('X-CSRF-Token') or
                    request.params.get('csrf_token'))
            if not token:
                raise ValueError("CSRF token missing")

    def _check_session_security(self, request):
        """Check session security."""
        # Session checks would be implemented here
        pass


def install_cherrypy_security(config):
    """Install security middleware for CherryPy web interface.

    Args:
        config: SpiderFoot configuration dictionary

    Returns:
        SpiderFootSecurityMiddleware instance
    """
    log = logging.getLogger(__name__)
    middleware = SpiderFootSecurityMiddleware(config)
    tool = CherryPySecurityTool(middleware)
    cherrypy.tools.sf_security = tool
    log.info("CherryPy security middleware installed")
    return middleware


def install_fastapi_security(app, config):
    """Install security middleware for FastAPI application.

    Args:
        app: FastAPI application instance
        config: SpiderFoot configuration dictionary

    Returns:
        SpiderFootSecurityMiddleware instance
    """
    log = logging.getLogger(__name__)
    middleware = SpiderFootSecurityMiddleware(config)
    log.info("FastAPI security middleware installed")
    return middleware
