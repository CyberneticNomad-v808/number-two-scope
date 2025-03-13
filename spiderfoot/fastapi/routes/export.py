"""SpiderFoot FastAPI Export Routes.

This module defines routes for exporting scan data.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, HTMLResponse

from spiderfoot.fastapi.core import SpiderFootAPI
from spiderfoot.fastapi.dependencies import get_sf_api, get_api_auth

# Create router with API key dependency
router = APIRouter(tags=["Export"], dependencies=[Depends(get_api_auth)])

@router.get("/scanexportlogs")
async def export_scan_logs(
    id: str, 
    dialect: str = "excel",
    sf_api: SpiderFootAPI = Depends(get_sf_api)
):
    """Export scan logs.

    Args:
        id: Scan ID
        dialect: CSV dialect
        sf_api: SpiderFoot API instance

    Returns:
        Response with CSV data
    """
    try:
        return await sf_api.export_scanexportlogs(id, dialect)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export logs: {str(e)}"
        )

@router.get("/scaneventresultexport")
async def export_scan_event_results(
    id: str,
    type: str,
    filetype: str = "csv",
    dialect: str = "excel",
    sf_api: SpiderFootAPI = Depends(get_sf_api)
):
    """Export scan event results.

    Args:
        id: Scan ID
        type: Event type
        filetype: Output file format (csv or excel)
        dialect: CSV dialect
        sf_api: SpiderFoot API instance

    Returns:
        Response with exported data
    """
    try:
        return await sf_api.export_scaneventresult(id, type, filetype, dialect)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export event results: {str(e)}"
        )

@router.get("/scanviz")
async def export_scan_visualization(
    id: str, 
    gexf: str = "0", 
    sf_api: SpiderFootAPI = Depends(get_sf_api)
):
    """Export scan visualization data.

    Args:
        id: Scan ID
        gexf: Format flag (0=JSON, 1=GEXF)
        sf_api: SpiderFoot API instance

    Returns:
        Response with visualization data
    """
    try:
        return await sf_api.export_scanviz(id, gexf)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export visualization: {str(e)}"
        )

@router.get("/scanvizmulti")
async def export_multi_scan_visualization(
    ids: str, 
    gexf: str = "1", 
    sf_api: SpiderFootAPI = Depends(get_sf_api)
):
    """Export visualization for multiple scans.

    Args:
        ids: Comma-separated scan IDs
        gexf: Format flag (0=JSON, 1=GEXF)
        sf_api: SpiderFoot API instance

    Returns:
        Response with visualization data
    """
    try:
        return await sf_api.export_scanvizmulti(ids, gexf)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export multi-scan visualization: {str(e)}"
        )
