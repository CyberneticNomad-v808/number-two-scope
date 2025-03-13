"""
SpiderFoot FastAPI Unit Tests

This module contains unit tests for the SpiderFoot FastAPI implementation.
"""

import unittest
from unittest.mock import Mock, patch
import json

from fastapi.testclient import TestClient

from spiderfoot.fastapi.app import create_app
from spiderfoot.fastapi.core import SpiderFootAPI
from spiderfoot.fastapi.models.scan import ScanCreate, ScanResponse


class TestSpiderFootFastApi(unittest.TestCase):
    """Test cases for SpiderFoot FastAPI implementation."""
    
    def setUp(self):
        """Set up test environment."""
        self.web_config = {
            'root': '/',
            'host': '127.0.0.1',
            'port': 5001,
            'debug': True,
        }
        
        self.sf_config = {
            '__modules__': {},
            '_debug': True,
        }
        
        # Create app with mock config
        with patch('spiderfoot.SpiderFootDb'):
            with patch('sflib.SpiderFoot'):
                self.app = create_app(self.web_config, self.sf_config)
                self.client = TestClient(self.app)
    
    def test_ping(self):
        """Test ping endpoint."""
        response = self.client.get("/ping")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data[0], "SUCCESS")
    
    def test_eventtypes(self):
        """Test eventtypes endpoint."""
        with patch('spiderfoot.SpiderFootDb') as mock_db:
            mock_db.return_value.eventTypes.return_value = [
                ("TEST_TYPE", "Test Type")
            ]
            response = self.client.get("/eventtypes")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data[0], ["Test Type", "TEST_TYPE"])
    
    def test_modules(self):
        """Test modules endpoint."""
        # Set up mock modules
        self.sf_config['__modules__'] = {
            'test_module': {
                'descr': 'Test Module'
            }
        }
        
        with patch('spiderfoot.SpiderFootDb'):
            with patch('sflib.SpiderFoot'):
                app = create_app(self.web_config, self.sf_config)
                client = TestClient(app)
                response = client.get("/modules")
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data[0]['name'], 'test_module')
                self.assertEqual(data[0]['descr'], 'Test Module')


class TestSpiderFootAPI(unittest.TestCase):
    """Test cases for SpiderFootAPI core class."""
    
    def setUp(self):
        """Set up test environment."""
        self.web_config = {
            'root': '/',
            'host': '127.0.0.1',
            'port': 5001,
            'debug': True,
        }
        
        self.sf_config = {
            '__modules__': {},
            '_debug': True,
        }
        
        # Create API with mock config
        with patch('spiderfoot.SpiderFootDb'):
            with patch('sflib.SpiderFoot'):
                with patch('multiprocessing.Queue'):
                    with patch('spiderfoot.logger.logListenerSetup'):
                        with patch('spiderfoot.logger.logWorkerSetup'):
                            self.api = SpiderFootAPI(self.web_config, self.sf_config)
    
    def test_clean_user_input(self):
        """Test cleanUserInput method."""
        test_data = ['<script>', 'normal text', '&quot;quoted&quot;']
        result = self.api.cleanUserInput(test_data)
        self.assertEqual(result[0], '&lt;script&gt;')
        self.assertEqual(result[1], 'normal text')
        self.assertEqual(result[2], '"quoted"')  # Quotes should be preserved


class TestRoutesIntegration(unittest.TestCase):
    """Integration tests for FastAPI routes."""
    
    def setUp(self):
        """Set up test environment."""
        self.web_config = {
            'root': '/',
            'host': '127.0.0.1',
            'port': 5001,
            'debug': True,
        }
        
        self.sf_config = {
            '__modules__': {
                'test_module': {
                    'descr': 'Test Module'
                }
            },
            '_debug': True,
        }
        
        # Create app with mock config
        with patch('spiderfoot.SpiderFootDb'):
            with patch('sflib.SpiderFoot'):
                with patch('multiprocessing.Queue'):
                    with patch('spiderfoot.logger.logListenerSetup'):
                        with patch('spiderfoot.logger.logWorkerSetup'):
                            self.app = create_app(self.web_config, self.sf_config)
                            self.client = TestClient(self.app)
    
    def test_start_scan(self):
        """Test starting a scan."""
        scan_data = {
            "scanname": "Test Scan",
            "scantarget": "example.com",
            "modulelist": "test_module",
            "usecase": "passive"
        }
        
        # Mock the scan process
        with patch('spiderfoot.fastapi.core.SpiderFootAPI.start_scan') as mock_scan:
            mock_scan.return_value = {"scan_id": "12345"}
            
            response = self.client.post(
                "/startscan",
                json=scan_data
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["scan_id"], "12345")
    
    def test_scan_list(self):
        """Test getting scan list."""
        with patch('spiderfoot.SpiderFootDb') as mock_db:
            mock_db.return_value.scanInstanceList.return_value = [
                [
                    "12345", "Test Scan", "example.com", 
                    1626000000, 1626000100, 1626001000, 
                    "FINISHED", 10
                ]
            ]
            mock_db.return_value.scanCorrelationSummary.return_value = []
            
            response = self.client.get("/scanlist")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0][0], "12345")
            self.assertEqual(data[0][1], "Test Scan")
