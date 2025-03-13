"""
SpiderFoot FastAPI Scan Routes

This module defines routes for managing scans (create, list, delete, etc.).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Security, status

from spiderfoot.fastapi.core import SpiderFootAPI
from spiderfoot.fastapi.dependencies import get_sf_api, get_api_auth
from spiderfoot.fastapi.models.scan import (
    ScanCreate, ScanResponse, ScanListItem, ScanDelete
)

# Create router
router = APIRouter(tags=["Scans"], dependencies=[Depends(get_api_auth)])


@router.post("/startscan", response_model=ScanResponse)
async def start_scan(
    scan_data: ScanCreate,
    sf_api: SpiderFootAPI = Depends(get_sf_api)
) -> dict:
    """Start a new scan.

    Args:
        scan_data: Scan configuration
        sf_api: SpiderFoot API instance

    Returns:
        Dict containing the scan ID
    """
    try:
        result = await sf_api.start_scan(
            scanname=scan_data.scanname,
            scantarget=scan_data.scantarget,
            modulelist=scan_data.modulelist,
            typelist=scan_data.typelist,
            usecase=scan_data.usecase
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scan: {str(e)}"
        )


@router.get("/scanlist", response_model=List[ScanListItem])
async def get_scan_list(sf_api: SpiderFootAPI = Depends(get_sf_api)) -> List:
    """Get a list of all scans.

    Args:
        sf_api: SpiderFoot API instance

    Returns:
        List of scan details
    """
    try:
        return await sf_api.get_scanlist()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scan list: {str(e)}"
        )


@router.delete("/scandelete", response_model=ScanDelete)
async def delete_scan(
    id: str,
    sf_api: SpiderFootAPI = Depends(get_sf_api)
) -> dict:
    """Delete one or more scans.

    Args:
        id: Comma-separated list of scan IDs
        sf_api: SpiderFoot API instance

    Returns:
        Status message
    """
    try:
        return await sf_api.delete_scan(id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete scan(s): {str(e)}"
        )


@router.post("/stopscan", response_model=ScanDelete)
async def stop_scan(
    id: str,
    sf_api: SpiderFootAPI = Depends(get_sf_api)
) -> dict:
    """Stop one or more running scans.

    Args:
        id: Comma-separated list of scan IDs
        sf_api: SpiderFoot API instance

    Returns:
        Status message
    """
    try:
        return await sf_api.stop_scan(id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop scan(s): {str(e)}"
        )
