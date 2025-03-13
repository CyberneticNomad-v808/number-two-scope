"""SpiderFoot FastAPI Application.

This module provides the application factory for creating and
configuring the FastAPI application instance.
"""

import logging
from typing import Dict, Any, Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware

from spiderfoot import __version__
from spiderfoot.fastapi.utils.logging import setup_logging
from spiderfoot.fastapi.utils.errors import setup_error_handlers
from spiderfoot.fastapi.utils.security import setup_cors, create_api_key_handler
from spiderfoot.fastapi.core import SpiderFootAPI
from spiderfoot.fastapi.dependencies import get_sf_api, initialize_sf_api

# Import all routes to register them
from spiderfoot.fastapi.routes import scan, search, config, ui, export


def create_app(web_config: Dict[str, Any], sf_config: Dict[str, Any]) -> FastAPI:
    """Create and configure a FastAPI application instance.

    Args:
        web_config: Web server configuration
        sf_config: SpiderFoot configuration

    Returns:
        FastAPI: Configured FastAPI application
    """
    app = FastAPI(
        title="SpiderFoot API",
        description="SpiderFoot OSINT Automation Tool API",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    # Add middlewares
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Initialize SpiderFoot API
    sf_api = initialize_sf_api(web_config, sf_config)

    # Set up utilities
    setup_logging(app, log_level=logging.DEBUG if sf_config.get(
        "_debug") else logging.INFO)
    setup_error_handlers(app, html_error_template=sf_api.error_html)
    setup_cors(
        app,
        allowed_origins=web_config.get(
            "cors", ["http://127.0.0.1", "http://localhost"])
    )

    # Set up API key authentication if enabled
    if web_config.get("enable_api_key_auth", False):
        create_api_key_handler(
            app,
            api_key=web_config.get("api_key"),
            show_api_key=web_config.get("show_api_key", False)
        )

    # Include all routers
    app.include_router(scan.router)
    app.include_router(search.router)
    app.include_router(config.router)
    app.include_router(ui.router)
    app.include_router(export.router)

    # Mount static files
    app.mount("/static", StaticFiles(directory="spiderfoot/static"), name="static")

    # Add application startup and shutdown events
    try:
        app = FastAPI(title="SpiderFoot API")
        
        # Register exception handler to catch and log startup errors
        @app.on_event("startup")
        async def startup_event():
            try:
                # Log successful startup
                print("FastAPI app starting up...")
                # Initialize any required resources
                # ...existing initialization code...
            except Exception as e:
                print(f"ERROR: FastAPI startup failed: {e}")
                import traceback
                print(traceback.format_exc())
                # Ensure the error propagates and stops the server
                raise

    except Exception as e:
        print(f"ERROR: Failed to initialize FastAPI application: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)

    @app.on_event("shutdown")
    async def shutdown_event():
        logger = logging.getLogger("spiderfoot.app")
        logger.info("Shutting down SpiderFoot FastAPI server")

    return app
