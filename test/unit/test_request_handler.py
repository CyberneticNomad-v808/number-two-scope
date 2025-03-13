"""Unit tests for spiderfoot.request_handler module."""

import unittest
from unittest import mock
import time
import requests

from spiderfoot.request_handler import RequestHandler


class TestRequestHandler(unittest.TestCase):
    """Test cases for RequestHandler class."""

    def setUp(self):
        """Set up test case."""
        self.opts = {"_useragent": "Mozilla/5.0 (Test)", "_fetchtimeout": 10}
        self.request_handler = RequestHandler(self.opts)

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.request_handler.opts, self.opts)
        self.assertIsNotNone(self.request_handler.session)
        self.assertIsNotNone(self.request_handler.log)

    def test_get_user_agent(self):
        """Test get_user_agent method."""
        # Test with string user agent
        self.assertEqual(self.request_handler.get_user_agent(),
                         "Mozilla/5.0 (Test)")

        # Test with list user agent
        handler = RequestHandler({"_useragent": ["Agent1", "Agent2"]})
        user_agent = handler.get_user_agent()
        self.assertIn(user_agent, ["Agent1", "Agent2"])

        # Test default user agent
        handler = RequestHandler({})
        self.assertTrue("Mozilla" in handler.get_user_agent())

    @mock.patch("requests.session")
    def test_create_session_with_proxy(self, mock_session):
        """Test _create_session method with proxy configuration."""
        mock_session_instance = mock.MagicMock()
        mock_session.return_value = mock_session_instance

        opts = {
            "_socks1type": "socks5",
            "_socks2addr": "localhost",
            "_socks3port": "9050",
            "_socks4user": "user",
            "_socks5pwd": "pass",
        }

        handler = RequestHandler(opts)

        mock_session_instance.proxies = {
            "http": "socks5://user:pass@localhost:9050",
            "https": "socks5://user:pass@localhost:9050",
        }

        self.assertEqual(handler.session, mock_session_instance)

    def test_sanitize_url_for_logging(self):
        """Test sanitize_url_for_logging method."""
        # Test URL with password
        url = "https://user:password@example.com"
        sanitized = self.request_handler.sanitize_url_for_logging(url)
        self.assertEqual(sanitized, "https://user:****@example.com")

        # Test URL with API key
        url = "https://example.com/api?apikey=12345&param=value"
        sanitized = self.request_handler.sanitize_url_for_logging(url)
        self.assertEqual(
            sanitized, "https://example.com/api?apikey=****&param=value")

        # Test normal URL
        url = "https://example.com/path"
        sanitized = self.request_handler.sanitize_url_for_logging(url)
        self.assertEqual(sanitized, "https://example.com/path")

        # Test invalid URL
        self.assertIsNone(self.request_handler.sanitize_url_for_logging(None))
        self.assertEqual(self.request_handler.sanitize_url_for_logging(""), "")

    @mock.patch("requests.get")
    def test_fetch_url(self, mock_get):
        """Test fetch_url method."""
        # Mock response
        mock_response = mock.MagicMock()
        mock_response.content = b"test content"
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_get.return_value = mock_response

        # Call fetch_url
        result = self.request_handler.fetch_url("https://example.com")

        # Check result
        self.assertEqual(result["content"], b"test content")
        self.assertEqual(result["code"], 200)
        self.assertEqual(result["headers"], {"Content-Type": "text/html"})
        self.assertIn("time", result)

        # Verify mock was called with correct arguments
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "https://example.com")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertIn("headers", kwargs)
        self.assertIn("User-Agent", kwargs["headers"])

    @mock.patch("requests.post")
    def test_fetch_url_post(self, mock_post):
        """Test fetch_url method with POST."""
        # Mock response
        mock_response = mock.MagicMock()
        mock_response.content = b"test content"
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_post.return_value = mock_response

        data = {"param": "value"}

        # Call fetch_url
        result = self.request_handler.fetch_url(
            "https://example.com", method="POST", data=data
        )

        # Check result
        self.assertEqual(result["content"], b"test content")
        self.assertEqual(result["code"], 200)

        # Verify mock was called with correct arguments
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://example.com")
        self.assertEqual(kwargs["data"], data)

    @mock.patch("requests.get")
    def test_fetch_url_with_error(self, mock_get):
        """Test fetch_url method with request error."""
        # Mock response
        mock_get.side_effect = requests.RequestException("Connection error")

        # Call fetch_url
        result = self.request_handler.fetch_url("https://example.com")

        # Check result
        self.assertIsNone(result["content"])
        self.assertIsNone(result["code"])
        self.assertIsNone(result["headers"])
        self.assertIn("time", result)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Connection error")

    @mock.patch("requests.get")
    def test_fetch_url_with_retry(self, mock_get):
        """Test fetch_url method with retry."""
        # First call fails, second succeeds
        mock_get.side_effect = [
            requests.RequestException("Connection error"),
            mock.MagicMock(
                content=b"test content",
                status_code=200,
                headers={"Content-Type": "text/html"},
            ),
        ]

        # Call fetch_url
        result = self.request_handler.fetch_url(
            "https://example.com", retry_times=1)

        # Check result
        self.assertEqual(result["content"], b"test content")
        self.assertEqual(result["code"], 200)
        self.assertEqual(mock_get.call_count, 2)

    @mock.patch("requests.get")
    @mock.patch("builtins.open", mock.mock_open())
    def test_download_file(self, mock_get):
        """Test download_file method."""
        # Mock response
        mock_response = mock.MagicMock()
        mock_response.content = b"file content"
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Set up fetch_url to return mock response
        self.request_handler.fetch_url = mock.MagicMock(
            return_value={"content": b"file content", "code": 200}
        )

        # Call download_file
        result = self.request_handler.download_file(
            "https://example.com/file", "/tmp/file"
        )

        # Verify result and mock calls
        self.assertTrue(result)
        self.request_handler.fetch_url.assert_called_once_with(
            "https://example.com/file", timeout=60
        )
        mock.mock_open().assert_called_once_with("/tmp/file", "wb")
        mock.mock_open().return_value.write.assert_called_once_with(b"file content")

    def test_check_url_exists(self):
        """Test check_url_exists method."""
        # Mock fetch_url for success
        self.request_handler.fetch_url = mock.MagicMock(
            return_value={"code": 200})
        self.assertTrue(self.request_handler.check_url_exists(
            "https://example.com"))

        # Mock fetch_url for redirect
        self.request_handler.fetch_url = mock.MagicMock(
            return_value={"code": 302})
        self.assertTrue(self.request_handler.check_url_exists(
            "https://example.com"))

        # Mock fetch_url for not found
        self.request_handler.fetch_url = mock.MagicMock(
            return_value={"code": 404})
        self.assertFalse(
            self.request_handler.check_url_exists("https://example.com"))

        # Mock fetch_url for exception
        self.request_handler.fetch_url = mock.MagicMock(
            side_effect=Exception("Error"))
        self.assertFalse(
            self.request_handler.check_url_exists("https://example.com"))


if __name__ == "__main__":
    unittest.main()
