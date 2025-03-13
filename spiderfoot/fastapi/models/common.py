"""
SpiderFoot FastAPI Common Models

This module defines common Pydantic models used across the API.
"""

from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """Generic API response model."""
    status: str = Field(description="Status of the operation (success/error)")
    message: Optional[str] = Field(None, description="Response message")


class ErrorDetail(BaseModel):
    """Error detail model."""
    type: str = Field(description="Error type")
    message: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """API error response model."""
    error: ErrorDetail


class StatusEnum(str, Enum):
    """Scan status enumeration."""
    STARTING = "STARTING"
    STARTED = "STARTED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"
    ABORT_REQUESTED = "ABORT-REQUESTED"
    

class RiskLevel(str, Enum):
    """Risk level enumeration."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class RiskMatrix(BaseModel):
    """Risk matrix model."""
    HIGH: int = 0
    MEDIUM: int = 0
    LOW: int = 0
    INFO: int = 0
