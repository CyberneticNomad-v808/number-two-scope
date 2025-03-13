"""
SpiderFoot FastAPI Testing Utilities

This module provides utilities for testing the SpiderFoot FastAPI implementation.
"""

import json
import os
import tempfile
from typing import Dict, Any, Optional, Union, List, Tuple
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from spiderfoot.fastapi.app import create_app
from spiderfoot.fastapi.core import SpiderFootAPI


def create_test_client(
    config: Optional[Dict[str, Any]] = None,
    web_config: Optional[Dict[str, Any]] = None,
    mock_db: bool = True
) -> TestClient:
    """Create a FastAPI TestClient for testing.
    
    Args:
        config: SpiderFoot configuration
        web_config: Web interface configuration
        mock_db: Whether to mock the database
        
    Returns:
        Test client for making requests
    """
    # Default configurations
    default_config = {
        "__modules__": {},
        "_debug": True,
    }
    
    default_web_config = {
        'root': '/',
        'host': '127.0.0.1',
        'port': 5001,
        'debug': True,
    }
    
    # Use provided configs or defaults
    test_config = config or default_config
    test_web_config = web_config or default_web_config
    
    # Create a test app
    if mock_db:
        from unittest.mock import patch
        with patch('spiderfoot.SpiderFootDb'), patch('sflib.SpiderFoot'):
            app = create_app(test_web_config, test_config)
            return TestClient(app)
    else:
        app = create_app(test_web_config, test_config)
        return TestClient(app)


def create_temp_config_file(config: Dict[str, Any]) -> str:
    """Create a temporary configuration file.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Path to temporary configuration file
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.conf')
    
    with open(temp_file.name, 'w', encoding='utf-8') as f:
        for key, value in config.items():
            if isinstance(value, dict):
                # Skip nested dictionaries as they need special handling
                continue
            f.write(f"{key}={value}\n")
    
    return temp_file.name


def mock_scan_result(
    scan_id: str, 
    scan_name: str = "Test Scan",
    target: str = "example.com",
    status: str = "FINISHED",
    started: int = 1625000000,
    ended: int = 1625001000,
    created: int = 1624999000,
    event_count: int = 10
) -> List[Any]:
    """Create a mock scan result.
    
    Args:
        scan_id: Scan ID
        scan_name: Scan name
        target: Scan target
        status: Scan status
        started: Start timestamp
        ended: End timestamp
        created: Creation timestamp
        event_count: Number of events
        
    Returns:
        Mock scan result
    """
    return [
        scan_id,
        scan_name,
        target,
        created,
        started,
        ended,
        status,
        event_count
    ]


def mock_scan_history(scan_id: str, points: int = 10) -> List[List[int]]:
    """Create mock scan history data.
    
    Args:
        scan_id: Scan ID
        points: Number of data points
        
    Returns:
        Mock scan history data
    """
    base_time = 1625000000
    history = []
    
    for i in range(points):
        timestamp = base_time + (i * 300)  # Every 5 minutes
        events = i * 5  # Increasing number of events
        history.append([timestamp, events])
    
    return history


def mock_api_response(
    scan_id: str, 
    event_count: int = 10,
    start_time: int = 1625000000
) -> List[List[Any]]:
    """Create a mock API response with event data.
    
    Args:
        scan_id: Scan ID
        event_count: Number of events
        start_time: Start timestamp
        
    Returns:
        Mock API response data
    """
    events = []
    
    for i in range(event_count):
        timestamp = start_time + (i * 60)  # Every minute
        event_type = "IP_ADDRESS" if i % 3 == 0 else "DOMAIN_NAME" if i % 3 == 1 else "URL"
        module = "sfp_dnsresolve" if i % 2 == 0 else "sfp_hunter"
        
        events.append([
            timestamp,
            f"data_{i}",  # Data
            f"source_{i}",  # Source
            module,  # Module
            event_type,  # Event type
            f"event_id_{i}",  # Event ID
            scan_id,  # Scan ID
            "Test scan", # Scan name
            "example.com",  # Scan target
            i,  # Source event ID
            0,  # False positive
            "INFO",  # Risk
            f"Data {i} from {module}", # Data description
            "",  # Correlation ID
            ""  # Correlation rule ID
        ])
    
    return events
