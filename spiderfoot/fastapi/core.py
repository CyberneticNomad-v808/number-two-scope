"""SpiderFoot FastAPI Core.

This module provides the core API functionality for the SpiderFoot
FastAPI implementation. It contains the SpiderFootAPI class which
encapsulates all API operations.
"""

import csv
import html
import json
import logging
import multiprocessing as mp
import random
import string
import time
from copy import deepcopy
from io import BytesIO, StringIO
from operator import itemgetter
from typing import Dict, List, Optional, Union, Any, Tuple

import openpyxl
import secure
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from mako.lookup import TemplateLookup
from mako.template import Template

from sflib import SpiderFoot
from sfscan import startSpiderFootScanner
from spiderfoot import SpiderFootDb, SpiderFootHelpers, __version__
from spiderfoot.logger import logListenerSetup, logWorkerSetup


class SpiderFootAPI:
    """SpiderFoot API core functionality."""

    def __init__(
        self,
        web_config: Dict[str, Any],
        config: Dict[str, Any],
        loggingQueue: Optional["mp.Queue"] = None,
    ) -> None:
        """Initialize the SpiderFoot API.

        Args:
            web_config: Web interface configuration settings
            config: SpiderFoot configuration
            loggingQueue: Optional logging queue for multiprocessing

        Raises:
            TypeError: If config or web_config is not a dictionary
            ValueError: If config or web_config is empty
        """
        if not isinstance(config, dict):
            raise TypeError(f"config is {type(config)}; expected dict()")
        if not config:
            raise ValueError("config is empty")

        if not isinstance(web_config, dict):
            raise TypeError(
                f"web_config is {type(web_config)}; expected dict()")
        if not config:
            raise ValueError("web_config is empty")

        self.docroot = web_config.get("root", "/").rstrip("/")

        # Initialize configuration
        self._init_config(config)

        # Initialize templates
        self.lookup = TemplateLookup(directories=[""])

        # Set up logging
        self._init_logging(loggingQueue)

        # Security setup
        self._init_security()

        # Generate a token for CSRF protection
        self.token = None

    def _init_config(self, config: Dict[str, Any]) -> None:
        """Initialize configuration.

        Args:
            config: SpiderFoot configuration
        """
        self.defaultConfig = deepcopy(config)
        dbh = SpiderFootDb(self.defaultConfig, init=True)
        sf = SpiderFoot(self.defaultConfig)
        self.config = sf.configUnserialize(dbh.configGet(), self.defaultConfig)

    def _init_logging(self, loggingQueue: Optional["mp.Queue"] = None) -> None:
        """Initialize logging.

        Args:
            loggingQueue: Optional logging queue for multiprocessing
        """
        if loggingQueue is None:
            self.loggingQueue = mp.Queue()
            logListenerSetup(self.loggingQueue, self.config)
        else:
            self.loggingQueue = loggingQueue
        logWorkerSetup(self.loggingQueue)
        self.log = logging.getLogger("spiderfoot.api.core")

    def _init_security(self) -> None:
        """Initialize security settings."""
        self.csp = (
            secure.ContentSecurityPolicy()
            .default_src("'self'")
            .script_src("'self'", "'unsafe-inline'", "blob:")
            .style_src("'self'", "'unsafe-inline'")
            .base_uri("'self'")
            .connect_src("'self'", "data:")
            .frame_src("'self'", "data:")
            .img_src("'self'", "data:")
        )

    def error_html(self, message: str) -> HTMLResponse:
        """Generate HTML error response.

        Args:
            message: Error message

        Returns:
            HTML error response
        """
        templ = Template(
            filename="spiderfoot/templates/error.tmpl", lookup=self.lookup)
        return HTMLResponse(
            content=templ.render(
                message=message,
                docroot=self.docroot,
                version=__version__
            )
        )

    def cleanUserInput(self, inputList: List[str]) -> List[str]:
        """Convert data to HTML entities; except quotes and ampersands.

        Args:
            inputList: List of strings to sanitize

        Returns:
            List of sanitized strings

        Raises:
            TypeError: If inputList is not a list
        """
        if not isinstance(inputList, list):
            raise TypeError(f"inputList is {type(inputList)}; expected list()")

        ret = []

        for item in inputList:
            if not item:
                ret.append("")
                continue
            c = html.escape(item, True)

            # Decode '&' and '"' HTML entities
            c = c.replace("&amp;", "&").replace("&quot;", '"')
            ret.append(c)

        return ret

    def reset_settings(self) -> bool:
        """Reset settings to default.

        Returns:
            True if successful, False otherwise
        """
        try:
            dbh = SpiderFootDb(self.config)
            dbh.configClear()  # Clear it in the DB
            self.config = deepcopy(self.defaultConfig)  # Clear in memory
        except Exception as e:
            self.log.error(f"Failed to reset settings: {e}", exc_info=True)
            return False

        return True

    # Additional core methods would be defined here...
