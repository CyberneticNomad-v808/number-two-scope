"""SpiderFoot FastAPI Security Tests.

This module contains unit tests for the SpiderFoot FastAPI security
features.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock

from fastapi.testclient import TestClient
from fastapi import FastAPI

from spiderfoot.fastapi.utils.security import (
    generate_api_key,
    setup_cors,
    APIKeyAuth,
    create_api_key_handler
)


class TestApiSecurity(unittest.TestCase):
    """Test cases for API security features."""

    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = generate_api_key()
        self.assertEqual(len(api_key), 32)
        
        # Test with custom length
        api_key = generate_api_key(length=16)
        self.assertEqual(len(api_key), 16)
        
        # Ensure keys are different
        api_key1 = generate_api_key()
        api_key2 = generate_api_key()
        self.assertNotEqual(api_key1, api_key2)

    def test_api_key_auth(self):
        """Test API key authentication."""
        test_key = "test_key_12345"
        auth = APIKeyAuth(api_key_name="X-Test-Key", api_key=test_key)
        
        # Test valid key
        self.assertTrue(auth.verify_api_key(test_key))
        
        # Test invalid key - should raise HTTPException
        with self.assertRaises(Exception):
            auth.verify_api_key("wrong_key")

    def test_api_endpoints_with_auth(self):
        """Test API endpoints with authentication."""
        app = FastAPI()
        test_key = "test_api_key"
        
        # Mock the dependency initialization
        with patch('spiderfoot.fastapi.dependencies.initialize_api_key_auth') as mock_init:
            mock_auth = MagicMock()
            mock_auth.api_key = test_key
            mock_auth.verify_api_key.side_effect = lambda k: k == test_key
            mock_init.return_value = mock_auth
            
            # Add a test endpoint with auth
            from spiderfoot.fastapi.utils.security import create_api_key_handler
            auth = create_api_key_handler(app, api_key=test_key)
            
            # Add dependency to endpoint
            from fastapi import Depends, Security
            from fastapi.security import APIKeyHeader
            
            @app.get("/test")
            def test_endpoint(api_key: str = Security(APIKeyHeader(name="X-API-Key"))):
                if not auth.verify_api_key(api_key):
                    return {"authenticated": False}
                return {"authenticated": True}
            
            # Test with client
            client = TestClient(app)
            
            # Test with valid key
            response = client.get("/test", headers={"X-API-Key": test_key})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"authenticated": True})
            
            # Test with invalid key - should return 401
            response = client.get("/test", headers={"X-API-Key": "invalid_key"})
            self.assertEqual(response.status_code, 401)
            
            # Test without key - should return 422 (validation error)
            response = client.get("/test")
            self.assertEqual(response.status_code, 422)
