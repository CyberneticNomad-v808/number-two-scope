"""
SpiderFoot FastAPI Main Module

This module provides the main entry point for the SpiderFoot FastAPI application.
"""

import logging
import os
import sys
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI

from spiderfoot import __version__
from spiderfoot.fastapi.app import create_app
from sflib import SpiderFoot


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load SpiderFoot configuration.
    
    Args:
        config_path: Path to configuration file
    
    Returns:
        SpiderFoot configuration dictionary
    
    Raises:
        SystemExit: If no configuration file could be found
    """
    # Search for config file in standard locations
    config_paths = [
        config_path,
        os.path.join(os.getcwd(), "spiderfoot.conf"),
        "/etc/spiderfoot.conf",
        "/usr/local/etc/spiderfoot.conf",
    ]
    
    # Filter out None values
    config_paths = [p for p in config_paths if p]
    
    # Try each path
    for path in config_paths:
        if os.path.isfile(path):
            return SpiderFoot.configSerialize(SpiderFoot.configUnserialize(path))
    
    print("Error: No configuration file found.")
    print("Tried: " + ", ".join(config_paths))
    sys.exit(1)


def run_app(
    host: str = "127.0.0.1",
    port: int = 5001,
    debug: bool = False,
    config_path: Optional[str] = None,
    **kwargs
) -> None:
    """Run the FastAPI application.
    
    Args:
        host: Host to listen on
        port: Port to listen on
        debug: Enable debug mode
        config_path: Path to configuration file
        **kwargs: Additional configuration options
    """
    # Load SpiderFoot configuration
    sf_config = load_config(config_path)
    sf_config["_debug"] = debug
    
    # Update with any additional options
    sf_config.update({k: v for k, v in kwargs.items() if not k.startswith("_")})
    
    # Web server configuration
    web_config = {
        "root": kwargs.get("root", "/"),
        "host": host,
        "port": port,
        "debug": debug,
        "enable_api_key_auth": kwargs.get("api_key_auth", False),
        "api_key": kwargs.get("api_key"),
        "show_api_key": kwargs.get("show_api_key", False),
        "cors": kwargs.get("cors", ["http://127.0.0.1", "http://localhost"])
    }
    
    # Create FastAPI application
    app = create_app(web_config, sf_config)
    
    # Configure logging
    log_level = "debug" if debug else "info"
    
    # Run the application
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        reload=debug
    )


def main() -> None:
    """Main entry point."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=f"SpiderFoot {__version__}")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
    parser.add_argument("-p", "--port", type=int, default=5001, help="Listen port (default: 5001)")
    parser.add_argument("-l", "--listen", default="127.0.0.1", help="Listen IP (default: 127.0.0.1)")
    parser.add_argument("-c", "--config", help="Path to configuration file")
    parser.add_argument("-k", "--api-key-auth", action="store_true", help="Enable API key authentication")
    parser.add_argument("--show-api-key", action="store_true", help="Show API key on startup")
    parser.add_argument("--cors", help="CORS allowed origins (comma-separated)")
    args = parser.parse_args()
    
    # Parse CORS origins
    cors = None
    if args.cors:
        cors = args.cors.split(",")
    
    # Run the application
    run_app(
        host=args.listen,
        port=args.port,
        debug=args.debug,
        config_path=args.config,
        api_key_auth=args.api_key_auth,
        show_api_key=args.show_api_key,
        cors=cors
    )


if __name__ == "__main__":
    main()
