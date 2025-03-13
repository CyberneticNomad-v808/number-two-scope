"""SpiderFoot FastAPI Settings Models.

This module defines models for API settings and configuration.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, root_validator


class ApiSettings(BaseModel):
    """API settings model."""
    enable_api_key_auth: bool = Field(
        False, 
        description="Enable API key authentication"
    )
    api_key: Optional[str] = Field(
        None, 
        description="API key for authentication"
    )
    show_api_key: bool = Field(
        False, 
        description="Show API key in logs on startup"
    )
    cors_origins: List[str] = Field(
        ["http://localhost", "http://127.0.0.1"], 
        description="CORS allowed origins"
    )
    debug: bool = Field(
        False, 
        description="Enable debug mode"
    )
    root: str = Field(
        "/", 
        description="API root path"
    )


class ModuleOptions(BaseModel):
    """Model for module options."""
    enabled: bool = Field(
        True, 
        description="Whether the module is enabled"
    )
    options: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Module-specific options"
    )


class SpiderFootConfig(BaseModel):
    """SpiderFoot configuration model."""
    modules: Dict[str, ModuleOptions] = Field(
        default_factory=dict,
        description="Module configurations"
    )
    global_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Global SpiderFoot options"
    )


class ConfigUpdateRequest(BaseModel):
    """Model for config update request."""
    config: Dict[str, Any] = Field(
        ...,
        description="Configuration to update"
    )
    token: str = Field(
        ...,
        description="CSRF token"
    )
    reset: bool = Field(
        False,
        description="Reset configuration to defaults"
    )


class TokenResponse(BaseModel):
    """Model for token response."""
    token: str = Field(
        ...,
        description="CSRF token"
    )
