"""
SpiderFoot FastAPI Request Models

This module defines Pydantic models for API requests.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class ScanRequest(BaseModel):
    """Model for scan request."""
    scanname: str = Field(
        ..., 
        description="Name for the scan"
    )
    scantarget: str = Field(
        ..., 
        description="Target for the scan"
    )
    modulelist: Optional[str] = Field(
        None, 
        description="Comma-separated list of modules"
    )
    typelist: Optional[str] = Field(
        None, 
        description="Comma-separated list of event types"
    )
    usecase: Optional[str] = Field(
        None, 
        description="Use case (all, passive, investigate, footprint)"
    )
    
    @validator("scanname", "scantarget")
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v
    
    @validator("usecase")
    def validate_usecase(cls, v):
        if v and v not in ["all", "passive", "investigate", "footprint"]:
            raise ValueError("Invalid use case")
        return v


class SearchRequest(BaseModel):
    """Model for search request."""
    scan_id: Optional[str] = Field(
        None,
        description="Scan ID to search within"
    )
    event_type: Optional[str] = Field(
        None,
        description="Event type to search for"
    )
    value: Optional[str] = Field(
        None,
        description="Value to search for (supports * as wildcard)"
    )
    regex: bool = Field(
        False,
        description="Whether to treat value as regex"
    )


class ExportRequest(BaseModel):
    """Model for export request."""
    scan_id: str = Field(
        ...,
        description="Scan ID to export"
    )
    event_type: Optional[str] = Field(
        None,
        description="Event type to export (if any)"
    )
    format: str = Field(
        "csv",
        description="Export format (csv, json, xlsx, gexf)"
    )
    
    @validator("format")
    def validate_format(cls, v):
        if v not in ["csv", "json", "xlsx", "gexf"]:
            raise ValueError("Invalid export format")
        return v
