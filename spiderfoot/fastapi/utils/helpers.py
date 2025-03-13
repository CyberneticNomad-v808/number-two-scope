"""SpiderFoot FastAPI Helper Utilities.

This module provides general helper functions for the SpiderFoot FastAPI
implementation.
"""

import os
import re
import time
import uuid
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime

def generate_unique_id() -> str:
    """Generate a unique ID.

    Returns:
        Unique ID string
    """
    return str(uuid.uuid4())

def format_timestamp(timestamp: Union[int, float]) -> str:
    """Format a Unix timestamp to a human-readable string.

    Args:
        timestamp: Unix timestamp

    Returns:
        Formatted timestamp string
    """
    # Handle None or 0 (not started/ended yet)
    if not timestamp:
        return "Not yet"
    
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

def sanitize_input(input_str: str) -> str:
    """Sanitize user input to prevent XSS and injection attacks.

    Args:
        input_str: User input string

    Returns:
        Sanitized string
    """
    if not input_str:
        return ""
    
    # Replace potentially harmful characters
    sanitized = input_str.replace("<", "&lt;").replace(">", "&gt;")
    
    return sanitized

def parse_comma_separated_list(input_str: str) -> List[str]:
    """Parse a comma-separated string into a list.

    Args:
        input_str: Comma-separated string

    Returns:
        List of strings
    """
    if not input_str:
        return []
    
    return [item.strip() for item in input_str.split(",") if item.strip()]

def is_valid_target(target: str) -> bool:
    """Check if a target is valid.

    Args:
        target: Target string

    Returns:
        True if target is valid
    """
    # Simple check - should be expanded based on SpiderFoot's actual rules
    if not target:
        return False
    
    # Remove quotes if present
    if target.startswith('"') and target.endswith('"'):
        target = target[1:-1]
    
    # Must have at least one character
    if len(target) < 1:
        return False
    
    return True

def build_pagination_links(
    current_page: int,
    total_pages: int,
    base_url: str
) -> Dict[str, Optional[str]]:
    """Build pagination links.

    Args:
        current_page: Current page number
        total_pages: Total number of pages
        base_url: Base URL for pagination links

    Returns:
        Dictionary of pagination links
    """
    links = {
        "first": f"{base_url}?page=1" if total_pages > 0 else None,
        "last": f"{base_url}?page={total_pages}" if total_pages > 0 else None,
        "prev": f"{base_url}?page={current_page - 1}" if current_page > 1 else None,
        "next": f"{base_url}?page={current_page + 1}" if current_page < total_pages else None
    }
    
    return links

def calculate_scan_duration(
    start_time: Union[int, float],
    end_time: Optional[Union[int, float]] = None
) -> str:
    """Calculate scan duration.

    Args:
        start_time: Scan start timestamp
        end_time: Scan end timestamp (or None if still running)

    Returns:
        Formatted duration string
    """
    if not start_time:
        return "Not started"
    
    # If end time is not provided or is 0, use current time
    if not end_time:
        end_time = time.time()
    
    duration_seconds = end_time - start_time
    
    # Format duration
    hours, remainder = divmod(duration_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    elif minutes > 0:
        return f"{int(minutes)}m {int(seconds)}s"
    else:
        return f"{int(seconds)}s"

def get_file_extension(filename: str) -> str:
    """Get file extension from filename.

    Args:
        filename: Filename

    Returns:
        File extension without dot
    """
    if not filename or "." not in filename:
        return ""
    
    return filename.split(".")[-1].lower()
