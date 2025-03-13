#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# Name:         sfwebui_fastapi_main
# Purpose:      Main entry point for FastAPI implementation of SpiderFoot UI
#
# Author:   Agostino Panico <van1sh@van1shland.io>
#
# Created:  01/03/2025
# Copyright:  (c) poppopjmp
# License:      MIT
# -----------------------------------------------------------------
"""SpiderFoot FastAPI Main Script.

This script serves as the main entry point for the SpiderFoot FastAPI
web interface. It delegates to the refactored modular implementation.
"""

from spiderfoot.fastapi.main import main as fastapi_main

if __name__ == "__main__":
    fastapi_main()
