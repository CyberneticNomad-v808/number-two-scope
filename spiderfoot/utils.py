"""
Shared utility functions for scan, workspace, and export operations.

This module provides common functions used across API routers and web UI
endpoints to reduce code duplication and improve maintainability.
"""

import csv
import time
import os
import glob
from io import StringIO
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def get_config_and_db(app_config_getter, config_dict):
    """Retrieve config and database connection.

    This is a common pattern used in multiple endpoints for retrieving
    application configuration and establishing database connections.

    Args:
        app_config_getter: Function to retrieve app config (e.g., get_app_config())
        config_dict: Optional pre-fetched config dictionary

    Returns:
        Tuple[AppConfig, SpiderFootDb]: Configuration and database objects

    Raises:
        Exception: If configuration retrieval fails
    """
    from spiderfoot import SpiderFootDb

    config = app_config_getter() if callable(app_config_getter) else app_config_getter
    db = SpiderFootDb(config.get_config() if hasattr(config, 'get_config') else config)
    return config, db


def expand_all_modules(modlist: List[str]) -> List[str]:
    """Expand 'all' meta-directive to list of all available modules.

    When a scan was originally started with 'all' modules, the _modulesenabled
    config stores 'all' literally. This function expands it to actual module names
    by scanning the modules directory.

    Args:
        modlist: List of module names (may contain 'all')

    Returns:
        List with 'all' replaced by actual module names
    """
    from spiderfoot import SpiderFootHelpers

    if 'all' not in modlist:
        return modlist

    # Remove 'all' from list
    modlist = [m for m in modlist if m != 'all']

    # Load modules directly from the modules directory
    try:
        modules = SpiderFootHelpers.loadModulesAsDict(
            SpiderFootHelpers.dataPath() + '/../modules',
            ['sfp_template.py']
        )
        all_modules = [m for m in modules.keys() if m.startswith('sfp_')]
    except Exception:
        # Fallback: scan the modules directory directly
        modules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../modules')
        all_modules = []
        for f in glob.glob(os.path.join(modules_dir, 'sfp_*.py')):
            mod_name = os.path.basename(f).replace('.py', '')
            if mod_name != 'sfp_template':
                all_modules.append(mod_name)

    # Extend with all modules (avoiding duplicates)
    for mod in all_modules:
        if mod not in modlist:
            modlist.append(mod)

    return modlist


def format_scan_event_row(row: Tuple, include_scan_name: bool = False,
                         scan_name: str = None) -> List[Any]:
    """Format a scan event database row for export.

    Standardizes the conversion of raw database rows into formatted data
    suitable for CSV/Excel export. Handles timestamp conversion and data
    field sanitization.

    Args:
        row: Database row tuple from scanResultEvent()
        include_scan_name: Whether to prepend scan name to the row
        scan_name: Scan name to prepend (if include_scan_name is True)

    Returns:
        List of formatted values ready for export
    """
    if row[4] == "ROOT":
        return None

    lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
    datafield = str(row[1]).replace("<SFURL>", "").replace("</SFURL>", "")

    formatted = [
        lastseen,
        str(row[4]),  # event_type
        str(row[3]),  # module
        str(row[2]),  # source_data
        row[13],      # false_positive flag
        datafield     # data
    ]

    if include_scan_name and scan_name:
        formatted.insert(0, scan_name)

    return formatted


def create_csv_writer(dialect: str = "excel") -> Tuple[StringIO, csv.writer]:
    """Create a CSV writer with standard configuration.

    Centralizes CSV writer creation to ensure consistent formatting
    across all export endpoints.

    Args:
        dialect: CSV dialect (default: "excel")

    Returns:
        Tuple[StringIO, csv.writer]: File object and configured writer
    """
    fileobj = StringIO()
    parser = csv.writer(fileobj, dialect=dialect)
    return fileobj, parser


def write_csv_headers(parser: csv.writer, headers: List[str]) -> None:
    """Write CSV headers.

    Args:
        parser: csv.writer object
        headers: List of header names
    """
    parser.writerow(headers)


def write_csv_row(parser: csv.writer, row: List[Any]) -> None:
    """Write a single CSV row, converting values to strings.

    Args:
        parser: csv.writer object
        row: List of values to write
    """
    parser.writerow([str(x) if x is not None else "" for x in row])


def format_search_event_row(row: List[Any]) -> List[Any]:
    """Format a search result database row for export.

    Converts search result rows (different format than scanResultEvent)
    into standardized export format.

    Args:
        row: Search result row from db.search()

    Returns:
        List of formatted values, or None if row is ROOT event
    """
    if len(row) < 12 or row[10] == "ROOT":
        return None

    datafield = str(row[1]).replace("<SFURL>", "").replace("</SFURL>", "")
    return [
        row[0],           # lastseen
        str(row[10]),     # event_type
        str(row[3]),      # module
        str(row[2]),      # source_data
        row[11],          # false_positive flag
        datafield         # data
    ]


def get_export_filename(base_name: str, scan_ids: List[str] = None,
                       scan_name: str = None, extension: str = "csv") -> str:
    """Generate appropriate export filename based on context.

    Args:
        base_name: Base filename without extension
        scan_ids: List of scan IDs (for multi-scan detection)
        scan_name: Scan name to include
        extension: File extension

    Returns:
        Formatted filename string
    """
    # Handle multi-scan case
    if scan_ids and len(scan_ids.split(',')) > 1:
        return f"SpiderFoot-multi.{extension}"

    # Single scan with name
    if scan_name:
        return f"{scan_name}-{base_name}.{extension}"

    # Default
    return f"SpiderFoot-{base_name}.{extension}"


def get_scan_instance(scan_id: str, db) -> Tuple[Any, bool]:
    """Safely retrieve scan instance from database.

    Standard pattern for retrieving and validating scan existence.

    Args:
        scan_id: Scan ID to retrieve
        db: SpiderFootDb instance

    Returns:
        Tuple[scan_info, exists]: Scan info and boolean indicating if found
    """
    try:
        scan_info = db.scanInstanceGet(scan_id)
        return scan_info, scan_info is not None
    except Exception as e:
        logger.error(f"Failed to retrieve scan {scan_id}: {e}")
        return None, False


def standardize_config_and_db(config_source, db_source=None):
    """Standardize config and DB retrieval pattern.

    Handles both cases: when config is already retrieved vs. when it needs
    to be retrieved from get_app_config().

    Args:
        config_source: Either AppConfig object or get_app_config function
        db_source: Optional pre-created database object

    Returns:
        Tuple[config_dict, db]: Raw config dictionary and database object
    """
    from spiderfoot import SpiderFootDb

    # Extract raw config
    if hasattr(config_source, 'get_config'):
        raw_config = config_source.get_config()
    elif isinstance(config_source, dict):
        raw_config = config_source
    else:
        # Assume it's callable (get_app_config)
        config_obj = config_source() if callable(config_source) else config_source
        raw_config = config_obj.get_config() if hasattr(config_obj, 'get_config') else config_obj

    # Use provided DB or create new one
    db = db_source if db_source else SpiderFootDb(raw_config)

    return raw_config, db
