"""SpiderFoot FastAPI API.

This module provides a simple interface to use SpiderFoot FastAPI
functionality from other Python code.
"""

from typing import Dict, Any, Optional

# Re-export the main components
from spiderfoot.fastapi.app import create_app
from spiderfoot.fastapi.main import run_app, load_config
from spiderfoot.fastapi.core import SpiderFootAPI

__all__ = ["create_app", "run_app", "load_config", "SpiderFootAPI", "create_server"]

def create_server(
    host: str = "127.0.0.1",
    port: int = 5001,
    debug: bool = False,
    config_path: Optional[str] = None,
    enable_api_key: bool = False,
    **kwargs
) -> None:
    """Create and run a SpiderFoot API server.

    This is a convenience function that loads the config and runs the app.

    Args:
        host: Host to listen on
        port: Port to listen on
        debug: Enable debug mode
        config_path: Path to configuration file
        enable_api_key: Enable API key authentication
        **kwargs: Additional configuration options

    Returns:
        None
    """
    # Set up API key auth if enabled
    api_key_opts = {}
    if enable_api_key:
        api_key_opts["api_key_auth"] = True
    
    # Run the app
    run_app(
        host=host,
        port=port,
        debug=debug,
        config_path=config_path,
        **api_key_opts,
        **kwargs
    )
