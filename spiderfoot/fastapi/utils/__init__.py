"""SpiderFoot FastAPI Utilities.

This package contains utilities for the FastAPI implementation:
- logging.py: Enhanced logging functionality
- errors.py: Error handling utilities
- security.py: Security utilities like API key authentication
- database.py: Database operations
- search.py: Search utilities
- visualization.py: Visualization helpers
- templates.py: Template utilities
- files.py: File operations
- helpers.py: General helpers
- testing.py: Testing utilities
"""

# Import directly used utilities for convenience
from spiderfoot.fastapi.utils.security import (
    generate_api_key,
    setup_cors,
    APIKeyAuth,
    create_api_key_handler
)

from spiderfoot.fastapi.utils.logging import (
    setup_logging,
    get_logger
)

from spiderfoot.fastapi.utils.errors import (
    setup_error_handlers,
    ErrorDetail
)

from spiderfoot.fastapi.utils.helpers import (
    generate_unique_id,
    format_timestamp,
    sanitize_input,
    parse_comma_separated_list,
    is_valid_target
)

__all__ = [
    # Security
    "generate_api_key", "setup_cors", "APIKeyAuth", "create_api_key_handler",
    
    # Logging
    "setup_logging", "get_logger",
    
    # Error handling
    "setup_error_handlers", "ErrorDetail",
    
    # Helpers
    "generate_unique_id", "format_timestamp", "sanitize_input", 
    "parse_comma_separated_list", "is_valid_target"
]
