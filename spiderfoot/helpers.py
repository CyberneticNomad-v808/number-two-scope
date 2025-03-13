#  -*- coding: utf-8 -*-
import html
import json
import os
import os.path
import random
import re
import ssl
import typing
import urllib.parse
import uuid
from pathlib import Path
import sys

try:
    from importlib import resources, files
except ImportError:
    try:
        # Try the importlib_resources backport if available
        import importlib_resources

        files = importlib_resources.files
    except ImportError:
        # Fallback implementation
        from importlib.resources import path as resources_path

        class FilesAdapter:
            def __init__(self, package):
                self.package = package

            def joinpath(self, resource):
                return resources_path(self.package, resource)

        def files(package):
            return FilesAdapter(package)


import networkx as nx
from bs4 import BeautifulSoup, SoupStrainer
from networkx.readwrite.gexf import GEXFWriter
import phonenumbers
import ipaddress


if sys.version_info >= (3, 8):  # PEP 589 support (TypedDict)

    class _GraphNode(typing.TypedDict):
        id: str  # noqa: A003
        label: str
        x: int
        y: int
        size: str
        color: str

    class _GraphEdge(typing.TypedDict):
        id: str  # noqa: A003
        source: str
        target: str

    class _Graph(typing.TypedDict, total=False):
        nodes: typing.List[_GraphNode]
        edges: typing.List[_GraphEdge]

    class Tree(typing.TypedDict):
        name: str
        children: typing.Optional[typing.List["Tree"]]

    class ExtractedLink(typing.TypedDict):
        source: str
        original: str

else:
    _GraphNode = typing.Dict[str, typing.Union[str, int]]

    _GraphEdge = typing.Dict[str, str]

    _GraphObject = typing.Union[_GraphNode, _GraphEdge]

    _Graph = typing.Dict[str, typing.List[_GraphObject]]

    _Tree_name = str

    _Tree_children = typing.Optional[typing.List["Tree"]]

    Tree = typing.Dict[str, typing.Union[_Tree_name, _Tree_children]]

    ExtractedLink = typing.Dict[str, str]


EmptyTree = typing.Dict[None, object]


class SpiderFootHelpers:
    """SpiderFoot helpers class.

    This class should contain your helper methods that were originally
    in the main module.
    """
    # Copy the implementation of SpiderFootHelpers from the original location
    pass

    @staticmethod
    def logPath() -> str:
        """
        Return the path to the log directory.
        
        Returns:
            str: Path to the SpiderFoot log directory
        """
        import os
        from pathlib import Path
        
        # Check if running from a Docker container
        if os.path.exists("/home/spiderfoot/log"):
            return "/home/spiderfoot/log"
        
        # Default to the user's home directory
        home_dir = str(Path.home())
        log_dir = os.path.join(home_dir, ".spiderfoot", "log")
        
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        return log_dir
