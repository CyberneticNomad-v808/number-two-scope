"""SpiderFoot FastAPI Configuration Models.

This module defines models for configuration-related operations.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from spiderfoot.fastapi.models.common import ApiResponse


class ConfigOptions(BaseModel):
    """Model for configuration options."""
    options: Dict[str, Any] = Field(..., description="Configuration options")


class ConfigResponse(ApiResponse):
    """Model for configuration response."""
    data: Optional[Any] = Field(None, description="Response data")


class ModuleInfo(BaseModel):
    """Model for module information."""
    name: str = Field(..., description="Module name")
    descr: str = Field(..., description="Module description")
    groups: List[str] = Field(default_factory=list,
                              description="Module groups")
    categories: List[str] = Field(
        default_factory=list, description="Module categories")
    provides: List[str] = Field(
        default_factory=list, description="Event types provided")
    consumes: List[str] = Field(
        default_factory=list, description="Event types consumed")
    meta: Dict[str, Any] = Field(
        default_factory=dict, description="Module metadata")
    options: Dict[str, Any] = Field(
        default_factory=dict, description="Module options")


class CorrelationRule(BaseModel):
    """Model for correlation rule."""
    id: str = Field(..., description="Rule ID")
    name: str = Field(..., description="Rule name")
    descr: str = Field(..., description="Rule description")
    risk: str = Field(..., description="Risk level")
