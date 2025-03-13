from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    """Model representing an error detail."""
    message: str
    code: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    """Model representing the error response."""
    detail: ErrorDetail
    status_code: int

def create_error_response(
    message: str, 
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    code: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create a standardized error response.
    
    Args:
        message: Error message
        status_code: HTTP status code
        code: Error code for client reference
        params: Additional parameters for the error
        
    Returns:
        JSONResponse with the error details
    """
    error_detail = ErrorDetail(message=message, code=code, params=params)
    content = ErrorResponse(detail=error_detail, status_code=status_code).dict()
    return JSONResponse(content=content, status_code=status_code)

def setup_error_handlers(app: FastAPI) -> None:
    """Setup global exception handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all uncaught exceptions."""
        return create_error_response(
            message=f"Internal Server Error: {str(exc)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_server_error"
        )
    
    @app.exception_handler(status.HTTP_404_NOT_FOUND)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle 404 Not Found errors."""
        return create_error_response(
            message=f"Resource not found: {request.url.path}",
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found"
        )
