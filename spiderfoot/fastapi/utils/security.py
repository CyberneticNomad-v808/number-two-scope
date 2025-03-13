"""
SpiderFoot FastAPI Security Utilities

This module provides security-related utilities for the FastAPI implementation.
"""

import random
import string
import logging
from typing import List, Optional, Union, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("spiderfoot.api.security")


def generate_api_key(length: int = 32) -> str:
    """Generate a random API key.
    
    Args:
        length: Length of the API key
    
    Returns:
        Random API key string
    """
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def setup_cors(
    app: FastAPI, 
    allowed_origins: List[str] = ["*"],
    allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE"],
    allowed_headers: List[str] = ["*"]
) -> None:
    """Set up CORS for the FastAPI application.
    
    Args:
        app: FastAPI application
        allowed_origins: List of allowed origins
        allowed_methods: List of allowed HTTP methods
        allowed_headers: List of allowed HTTP headers
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=allowed_methods,
        allow_headers=allowed_headers,
    )


class APIKeyAuth:
    """API key authentication class for FastAPI."""
    
    def __init__(self, api_key_name: str = "X-API-Key", api_key: Optional[str] = None):
        """Initialize API key authentication.
        
        Args:
            api_key_name: API key header name
            api_key: API key value (if None, a random key will be generated)
        """
        self.api_key_name = api_key_name
        self.api_key_header = APIKeyHeader(name=api_key_name, auto_error=True)
        self.api_key = api_key or generate_api_key()
    
    def verify_api_key(self, api_key: str) -> bool:
        """Verify API key.
        
        Args:
            api_key: API key to verify
            
        Returns:
            True if API key is valid
            
        Raises:
            HTTPException: If API key is invalid
        """
        if not self.api_key or api_key != self.api_key:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid API key",
                headers={"WWW-Authenticate": f"{self.api_key_name}"},
            )
        return True


def create_api_key_handler(
    app: FastAPI, 
    api_key: Optional[str] = None, 
    show_api_key: bool = False
) -> APIKeyAuth:
    """Create an API key handler for the FastAPI application.
    
    Args:
        app: FastAPI application
        api_key: API key (if None, a random key will be generated)
        show_api_key: Whether to log the API key
        
    Returns:
        APIKeyAuth instance
    """
    from spiderfoot.fastapi.dependencies import initialize_api_key_auth
    
    # Generate API key if not provided
    if api_key is None:
        api_key = generate_api_key()
    
    # Initialize API key auth
    api_key_auth = initialize_api_key_auth(api_key_name="X-API-Key", api_key=api_key)
    
    # Log API key if requested
    if show_api_key:
        logger.info(f"API Key: {api_key}")
    
    return api_key_auth
