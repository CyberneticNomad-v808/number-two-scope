"""SpiderFoot FastAPI CLI.

This module provides command-line integration for the SpiderFoot FastAPI
implementation.
"""

import argparse
import os
import sys
from typing import List, Dict, Any, Optional, Tuple

from spiderfoot import __version__
from spiderfoot.fastapi.main import run_app


def parse_args() -> Tuple[argparse.Namespace, Dict[str, Any]]:
    """Parse command line arguments.

    Returns:
        Tuple of parsed arguments and configuration options
    """
    parser = argparse.ArgumentParser(description=f"SpiderFoot {__version__}")
    
    # Server options
    server_group = parser.add_argument_group("Server")
    server_group.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
    server_group.add_argument("-p", "--port", type=int, default=5001, help="Listen port (default: 5001)")
    server_group.add_argument("-l", "--listen", default="127.0.0.1", help="Listen IP (default: 127.0.0.1)")
    server_group.add_argument("-r", "--root", default="/", help="Root path for the application")
    
    # Configuration
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument("-c", "--config", help="Path to configuration file")
    
    # Security
    security_group = parser.add_argument_group("Security")
    security_group.add_argument("-k", "--api-key-auth", action="store_true", help="Enable API key authentication")
    security_group.add_argument("--api-key", help="Specify API key (default: auto-generated)")
    security_group.add_argument("--show-api-key", action="store_true", help="Show API key on startup")
    security_group.add_argument("--cors", help="CORS allowed origins (comma-separated)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Collect config options
    config_opts = {}
    
    # Parse CORS origins
    if args.cors:
        config_opts["cors"] = args.cors.split(",")
    
    return args, config_opts


def main() -> None:
    """Main entry point for CLI."""
    args, config_opts = parse_args()
    
    # Run the application
    run_app(
        host=args.listen,
        port=args.port,
        debug=args.debug,
        config_path=args.config,
        root=args.root,
        api_key_auth=args.api_key_auth,
        api_key=args.api_key,
        show_api_key=args.show_api_key,
        **config_opts
    )


if __name__ == "__main__":
    main()
