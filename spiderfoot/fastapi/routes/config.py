"""SpiderFoot FastAPI Configuration Routes.

This module defines routes for managing SpiderFoot configuration.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Form, UploadFile, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse

from spiderfoot.fastapi.core import SpiderFootAPI
from spiderfoot.fastapi.dependencies import get_sf_api, get_api_auth
from spiderfoot.fastapi.models.config import ConfigOptions, ConfigResponse

# Create router with API key dependency
router = APIRouter(tags=["Configuration"], dependencies=[Depends(get_api_auth)])

@router.post("/savesettings")
async def save_settings(
    request: Request,
    allopts: str = Form(...),
    token: str = Form(...),
    configFile: Optional[UploadFile] = None,
    sf_api: SpiderFootAPI = Depends(get_sf_api)
):
    """Save system settings.

    Args:
        request: FastAPI request
        allopts: JSON string of settings
        token: CSRF token
        configFile: Optional configuration file
        sf_api: SpiderFoot API instance

    Returns:
        Redirect to settings page or error message
    """
    try:
        return await sf_api.save_settings(allopts, token, configFile)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save settings: {str(e)}"
        )

@router.post("/savesettingsraw", response_model=ConfigResponse)
async def save_settings_raw(
    config_data: ConfigOptions,
    token: str,
    sf_api: SpiderFootAPI = Depends(get_sf_api)
):
    """Save settings via raw API call.

    Args:
        config_data: Configuration options
        token: CSRF token
        sf_api: SpiderFoot API instance

    Returns:
        Response with status
    """
    try:
        result = await sf_api.save_settings_raw(config_data.options, token)
        return {"status": "SUCCESS", "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save settings: {str(e)}"
        )

@router.get("/optsraw", response_model=Dict[str, Any])
async def get_options_raw(sf_api: SpiderFootAPI = Depends(get_sf_api)):
    """Get raw configuration options.

    Args:
        sf_api: SpiderFoot API instance

    Returns:
        Dictionary of configuration options
    """
    try:
        sf_api.token = sf_api.token or sf_api.generate_token()
        return {
            "status": "SUCCESS",
            "data": {
                "token": sf_api.token,
                "options": sf_api.get_options()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get options: {str(e)}"
        )
