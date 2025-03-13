"""SpiderFoot FastAPI Search Routes.

This module defines routes for search functionality.
"""

from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status

from spiderfoot.fastapi.core import SpiderFootAPI
from spiderfoot.fastapi.dependencies import get_sf_api, get_api_auth

# Create router with API key dependency
router = APIRouter(prefix="/search", tags=["Search"], dependencies=[Depends(get_api_auth)])

@router.get("/", response_model=List[List[Any]])
async def search(
    id: Optional[str] = None, 
    eventType: Optional[str] = None,
    value: Optional[str] = None,
    sf_api: SpiderFootAPI = Depends(get_sf_api)
):
    """Search for data across scans.

    Args:
        id: Filter by scan ID
        eventType: Filter by event type
        value: Filter by value

    Returns:
        List of search results
    """
    try:
        return await sf_api.search_data(id, eventType, value)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}"
        )

@router.get("/history", response_model=List[Any])
async def get_scan_history(
    id: str,
    sf_api: SpiderFootAPI = Depends(get_sf_api)
):
    """Get historical data for a scan.

    Args:
        id: Scan ID

    Returns:
        List of historical data points
    """
    try:
        return await sf_api.get_scanhistory(id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scan history: {str(e)}"
        )
