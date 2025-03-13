"""SpiderFoot FastAPI Scan Models.

This module defines Pydantic models for scan-related operations.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, AnyHttpUrl

from spiderfoot.fastapi.models.common import StatusEnum, RiskMatrix


class ScanCreate(BaseModel):
    """Model for creating a new scan."""
    scanname: str = Field(description="Name for the scan")
    scantarget: str = Field(description="Target for the scan")
    modulelist: Optional[str] = Field(
        None, description="Comma-separated list of modules")
    typelist: Optional[str] = Field(
        None, description="Comma-separated list of types")
    usecase: Optional[str] = Field(
        None, description="Use case (all, passive, investigate, footprint)")


class ScanResponse(BaseModel):
    """Model for scan creation response."""
    scan_id: str = Field(description="Scan ID")


class ScanInfo(BaseModel):
    """Model for scan information."""
    id: str = Field(description="Scan ID")
    name: str = Field(description="Scan name")
    target: str = Field(description="Scan target")
    created: datetime = Field(description="Scan creation time")
    started: Union[datetime, str] = Field(description="Scan start time")
    finished: Union[datetime, str] = Field(description="Scan finish time")
    status: StatusEnum = Field(description="Scan status")
    total_events: int = Field(description="Total number of events")
    risk_matrix: RiskMatrix = Field(description="Risk breakdown")


class ScanListItem(BaseModel):
    """Model for scan list item."""
    id: str
    name: str
    target: str
    created: str
    started: str
    finished: str
    status: str
    total_events: int
    risk_matrix: RiskMatrix


class ScanDelete(BaseModel):
    """Model for scan deletion response."""
    status: str = Field(description="Operation status")
    message: str = Field(description="Operation message")
