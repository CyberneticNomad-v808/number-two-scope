"""SpiderFoot FastAPI Template Utilities.

This module provides utilities for working with templates in the FastAPI
implementation.
"""

import os
from typing import Any, Dict, Optional, Union, List
from fastapi import Request
from fastapi.templating import Jinja2Templates
from mako.lookup import TemplateLookup
from mako.template import Template
from fastapi.responses import HTMLResponse

from spiderfoot import __version__


class TemplateManager:
    """Template manager for SpiderFoot FastAPI implementation."""

    def __init__(
        self,
        template_dir: str = "spiderfoot/templates",
        mako_dirs: Optional[List[str]] = None
    ):
        """Initialize template manager.

        Args:
            template_dir: Directory containing Jinja2 templates
            mako_dirs: Directories containing Mako templates
        """
        self.jinja2_templates = Jinja2Templates(directory=template_dir)
        self.mako_lookup = TemplateLookup(directories=mako_dirs or [""])

    def render_jinja2(
        self,
        request: Request,
        template_name: str,
        context: Dict[str, Any] = None
    ) -> HTMLResponse:
        """Render a Jinja2 template.

        Args:
            request: FastAPI request
            template_name: Name of template file
            context: Template context

        Returns:
            HTMLResponse: Rendered template
        """
        context = context or {}
        context.update({
            "request": request,
            "version": __version__
        })
        return self.jinja2_templates.TemplateResponse(template_name, context)

    def render_mako(
        self,
        template_name: str,
        context: Dict[str, Any] = None
    ) -> HTMLResponse:
        """Render a Mako template.

        Args:
            template_name: Name of template file
            context: Template context

        Returns:
            HTMLResponse: Rendered template
        """
        context = context or {}
        context.update({
            "version": __version__
        })

        templ = Template(filename=template_name, lookup=self.mako_lookup)
        return HTMLResponse(content=templ.render(**context))

    def render_error(self, message: str, docroot: str = "/") -> HTMLResponse:
        """Render error template.

        Args:
            message: Error message
            docroot: Document root path

        Returns:
            HTMLResponse: Rendered error template
        """
        templ = Template(
            filename="spiderfoot/templates/error.tmpl",
            lookup=self.mako_lookup
        )
        return HTMLResponse(
            content=templ.render(
                message=message,
                docroot=docroot,
                version=__version__
            )
        )
