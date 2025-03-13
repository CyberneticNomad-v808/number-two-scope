#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# Name:         sf_fastapi
# Purpose:      Main entry point for FastAPI-based SpiderFoot
#
# Author:   Agostino Panico <van1sh@van1shland.io>
#
# Created:  01/03/2025
# Copyright:  (c) poppopjmp
# License:      MIT
# -----------------------------------------------------------------
import os
import sys
import logging
import argparse
from sfwebui_fastapi_main import main as fastapi_main


def main():
    """Main function to start the FastAPI application."""
    desc = f"SpiderFoot: Open Source Intelligence Automation."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        "-d", "--debug", help="Enable debug output.", action='store_true')
    parser.add_argument("-l", metavar="IP:port",
                        help="IP and port to listen on.")
    parser.add_argument("-m", metavar="mod1,mod2,...",
                        type=str, help="Modules to enable.")
    parser.add_argument("-M", "--modules",
                        help="List available modules.", action='store_true')
    parser.add_argument("-s", metavar="TARGET", help="Target for the scan.")
    parser.add_argument("-t", metavar="type1,type2,...",
                        type=str, help="Event types to collect.")
    parser.add_argument(
        "-T", "--types", help="List available event types.", action='store_true')
    parser.add_argument("-o", metavar="tab|csv|json",
                        type=str, help="Output format.")
    parser.add_argument("-n", metavar="Name", help="Name for the scan.")
    parser.add_argument("-r", help="Data directory", type=str)
    parser.add_argument(
        "-c", "--correlate", help="Run correlation rules against scan results.", action='store_true')
    parser.add_argument("-f", help="Disable DNS cache.", action='store_true')
    args = parser.parse_args()

    # Use FastAPI instead of CherryPy
    if True:  # Always use FastAPI in this version
        fastapi_main()
        return


if __name__ == "__main__":
    main()
