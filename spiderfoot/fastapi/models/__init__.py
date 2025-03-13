"""SpiderFoot FastAPI Models.

This package contains Pydantic models for request/response validation.
- scan: Scan-related models
- config: Configuration models
- common: Common models used across multiple areas
- settings: Settings and configuration models
- requests: Request models
"""

# Import common models for convenience
from spiderfoot.fastapi.models.common import (
    ApiResponse,
    ErrorDetail,
    ErrorResponse,
    StatusEnum,
    RiskLevel,
    RiskMatrix
)

# Import scan-related models
from spiderfoot.fastapi.models.scan import (
    ScanCreate,
    ScanResponse,
    ScanInfo,
    ScanListItem,
    ScanDelete
)

# Import configuration models
from spiderfoot.fastapi.models.config import (
    ConfigOptions,
    ConfigResponse,
    ModuleInfo,
    CorrelationRule
)

# Import settings models
from spiderfoot.fastapi.models.settings import (
    ApiSettings,
    ModuleOptions,
    SpiderFootConfig,
    ConfigUpdateRequest,
    TokenResponse
)

# Import request models
from spiderfoot.fastapi.models.requests import (
    ScanRequest,
    SearchRequest,
    ExportRequest
)

__all__ = [
    # Common models
    "ApiResponse", "ErrorDetail", "ErrorResponse", "StatusEnum", "RiskLevel", "RiskMatrix",
    
    # Scan models
    "ScanCreate", "ScanResponse", "ScanInfo", "ScanListItem", "ScanDelete",
    
    # Config models
    "ConfigOptions", "ConfigResponse", "ModuleInfo", "CorrelationRule",
    
    # Settings models
    "ApiSettings", "ModuleOptions", "SpiderFootConfig", "ConfigUpdateRequest", "TokenResponse",
    
    # Request models
    "ScanRequest", "SearchRequest", "ExportRequest"
]
