"""
SpiderFoot FastAPI UI Routes

This module defines routes for the HTML user interface.
"""

from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

from spiderfoot.fastapi.core import SpiderFootAPI
from spiderfoot.fastapi.dependencies import get_sf_api, get_api_auth

# Create router with API key dependency (optional for UI routes)
router = APIRouter(tags=["UI"], dependencies=[Depends(get_api_auth)])

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, sf_api: SpiderFootAPI = Depends(get_sf_api)):
    """Show scan list page.

    Returns:
        HTMLResponse: Scan list page
    """
    try:
        return await sf_api.render_index(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rendering page: {str(e)}"
        )

@router.get("/scaninfo", response_class=HTMLResponse)
async def scan_info(request: Request, id: str, sf_api: SpiderFootAPI = Depends(get_sf_api)):
    """Show information about a scan.

    Args:
        request: FastAPI request
        id: Scan ID
        sf_api: SpiderFoot API instance

    Returns:
        HTMLResponse: Scan info page
    """
    try:
        return await sf_api.render_scaninfo(request, id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rendering page: {str(e)}"
        )

@router.get("/newscan", response_class=HTMLResponse)
async def new_scan(request: Request, sf_api: SpiderFootAPI = Depends(get_sf_api)):
    """Show new scan configuration page.

    Args:
        request: FastAPI request
        sf_api: SpiderFoot API instance

    Returns:
        HTMLResponse: New scan page
    """
    try:
        return await sf_api.render_newscan(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rendering page: {str(e)}"
        )

@router.get("/clonescan", response_class=HTMLResponse)
async def clone_scan(request: Request, id: str, sf_api: SpiderFootAPI = Depends(get_sf_api)):
    """Show clone scan configuration page with pre-populated options.

    Args:
        request: FastAPI request
        id: ID of scan to clone
        sf_api: SpiderFoot API instance

    Returns:
        HTMLResponse: Clone scan page
    """
    try:
        return await sf_api.render_clonescan(request, id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rendering page: {str(e)}"
        )

@router.get("/opts", response_class=HTMLResponse)
async def settings(
    request: Request, 
    updated: Optional[str] = None,
    sf_api: SpiderFootAPI = Depends(get_sf_api)
):
    """Show settings page.

    Args:
        request: FastAPI request
        updated: Whether settings were updated successfully
        sf_api: SpiderFoot API instance

    Returns:
        HTMLResponse: Settings page
    """
    try:
        return await sf_api.render_opts(request, updated)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rendering page: {str(e)}"
        )
