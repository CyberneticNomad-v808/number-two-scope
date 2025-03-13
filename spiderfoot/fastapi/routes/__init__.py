"""SpiderFoot FastAPI Routes.

This package contains FastAPI route handlers organized by domain:
- scan: Scan management routes
- search: Search-related routes
- config: Configuration routes
- ui: HTML UI routes
- export: Data export routes
"""

# Import all route modules to register them
from spiderfoot.fastapi.routes import scan
from spiderfoot.fastapi.routes import search
from spiderfoot.fastapi.routes import config
from spiderfoot.fastapi.routes import ui
from spiderfoot.fastapi.routes import export

# Export all router instances for app.include_router()
routers = [
    scan.router,
    search.router,
    config.router,
    ui.router,
    export.router
]

__all__ = [
    "scan",
    "search",
    "config",
    "ui",
    "export",
    "routers"
]
