"""SpiderFoot FastAPI Dependencies.

This module provides dependency functions for FastAPI dependency
injection.
"""

from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from spiderfoot.fastapi.core import SpiderFootAPI
from spiderfoot.fastapi.utils.security import APIKeyAuth

# Global API instance
_sf_api_instance: Optional[SpiderFootAPI] = None
_api_key_auth: Optional[APIKeyAuth] = None


def initialize_sf_api(web_config: Dict[str, Any], config: Dict[str, Any]) -> SpiderFootAPI:
    """Initialize the global SpiderFootAPI instance.

    Args:
        web_config: Web interface configuration
        config: SpiderFoot configuration

    Returns:
        SpiderFootAPI: The initialized SpiderFootAPI instance
    """
    global _sf_api_instance
    _sf_api_instance = SpiderFootAPI(web_config, config)
    return _sf_api_instance


def initialize_api_key_auth(api_key_name: str = "X-API-Key", api_key: Optional[str] = None) -> APIKeyAuth:
    """Initialize the global API key authentication handler.

    Args:
        api_key_name: Name of the API key header
        api_key: The API key to use for authentication

    Returns:
        APIKeyAuth: The initialized API key auth handler
    """
    global _api_key_auth
    _api_key_auth = APIKeyAuth(api_key_name=api_key_name, api_key=api_key)
    return _api_key_auth


def get_sf_api() -> SpiderFootAPI:
    """Get the SpiderFootAPI instance.

    Returns:
        SpiderFootAPI: The global SpiderFootAPI instance

    Raises:
        HTTPException: If the API instance is not initialized
    """
    global _sf_api_instance
    if _sf_api_instance is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SpiderFoot API not initialized"
        )
    return _sf_api_instance


def get_api_auth(api_key: str = Security(APIKeyHeader(name="X-API-Key"))) -> bool:
    """Verify API key authentication.

    Args:
        api_key: API key from header

    Returns:
        bool: True if authentication successful

    Raises:
        HTTPException: If the API key is invalid
    """
    global _api_key_auth
    if _api_key_auth:
        return _api_key_auth.verify_api_key(api_key)
    return True
