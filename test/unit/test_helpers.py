"""Unit tests for spiderfoot.helpers module."""

import os
import unittest
import tempfile
from pathlib import Path
from unittest import mock

from spiderfoot.helpers import SpiderFootHelpers


class TestSpiderFootHelpers(unittest.TestCase):
    """Test cases for SpiderFootHelpers class."""

    def setUp(self):
        """Set up test case."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after test case."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @mock.patch('os.getenv')
    @mock.patch('os.path.isdir')
    @mock.patch('os.makedirs')
    def test_data_path(self, mock_makedirs, mock_isdir, mock_getenv):
        """Test dataPath method."""
        # Test when environment variable is set
        mock_getenv.return_value = "/custom/data/path"
        mock_isdir.return_value = True
        self.assertEqual(SpiderFootHelpers.dataPath(), "/custom/data/path")

        # Test when environment variable is not set
        mock_getenv.return_value = None
        mock_isdir.return_value = True
        home_dir = str(Path.home())
        self.assertEqual(SpiderFootHelpers.dataPath(), f"{home_dir}/.spiderfoot")

        # Test directory creation
        mock_isdir.return_value = False
        SpiderFootHelpers.dataPath()
        mock_makedirs.assert_called_once()

    @mock.patch('os.getenv')
    @mock.patch('os.path.isdir')
    @mock.patch('os.makedirs')
    def test_log_path(self, mock_makedirs, mock_isdir, mock_getenv):
        """Test logPath method."""
        # Test when environment variable is set
        mock_getenv.return_value = "/custom/logs/path"
        mock_isdir.return_value = True
        self.assertEqual(SpiderFootHelpers.logPath(), "/custom/logs/path")

        # Test when environment variable is not set
        mock_getenv.return_value = None
        mock_isdir.return_value = True
        home_dir = str(Path.home())
        self.assertEqual(SpiderFootHelpers.logPath(), f"{home_dir}/.spiderfoot/logs")

        # Test directory creation
        mock_isdir.return_value = False
        SpiderFootHelpers.logPath()
        mock_makedirs.assert_called_once()

    def test_target_type_from_string(self):
        """Test targetTypeFromString method."""
        # Test valid target types
        self.assertEqual(SpiderFootHelpers.targetTypeFromString("192.168.1.1"), "IP_ADDRESS")
        self.assertEqual(SpiderFootHelpers.targetTypeFromString("example.com"), "INTERNET_NAME")
        self.assertEqual(SpiderFootHelpers.targetTypeFromString("user@example.com"), "EMAILADDR")
        self.assertEqual(SpiderFootHelpers.targetTypeFromString("192.168.1.0/24"), "NETBLOCK_OWNER")
        self.assertEqual(SpiderFootHelpers.targetTypeFromString("AS12345"), "BGP_AS_OWNER")
        self.assertEqual(SpiderFootHelpers.targetTypeFromString("2001:db8::1"), "IPV6_ADDRESS")

        # Test invalid target types
        self.assertIsNone(SpiderFootHelpers.targetTypeFromString(""))
        self.assertIsNone(SpiderFootHelpers.targetTypeFromString(None))
        self.assertIsNone(SpiderFootHelpers.targetTypeFromString("invalid"))

    def test_url_relative_to_absolute(self):
        """Test urlRelativeToAbsolute method."""
        base_url = "https://example.com/path/to/page.html"
        
        # Test relative URL
        relative_url = "../images/logo.png"
        expected = "https://example.com/path/images/logo.png"
        self.assertEqual(SpiderFootHelpers.urlRelativeToAbsolute(base_url, relative_url), expected)
        
        # Test already absolute URL
        absolute_url = "https://another.com/path/image.png"
        self.assertEqual(SpiderFootHelpers.urlRelativeToAbsolute(base_url, absolute_url), absolute_url)
        
        # Test invalid inputs
        self.assertIsNone(SpiderFootHelpers.urlRelativeToAbsolute(None, "path"))
        self.assertIsNone(SpiderFootHelpers.urlRelativeToAbsolute("", "path"))
        self.assertIsNone(SpiderFootHelpers.urlRelativeToAbsolute("https://example.com", None))
        self.assertIsNone(SpiderFootHelpers.urlRelativeToAbsolute("https://example.com", ""))

    def test_url_base_dir(self):
        """Test urlBaseDir method."""
        # Test with file URL
        url = "https://example.com/path/to/file.html"
        self.assertEqual(SpiderFootHelpers.urlBaseDir(url), "https://example.com/path/to/")
        
        # Test with directory URL (ending with slash)
        url = "https://example.com/path/to/"
        self.assertEqual(SpiderFootHelpers.urlBaseDir(url), "https://example.com/path/to/")
        
        # Test with root URL
        url = "https://example.com"
        self.assertEqual(SpiderFootHelpers.urlBaseDir(url), "https://example.com/")
        
        # Test invalid inputs
        self.assertIsNone(SpiderFootHelpers.urlBaseDir(None))
        self.assertIsNone(SpiderFootHelpers.urlBaseDir(""))

    def test_url_base_url(self):
        """Test urlBaseUrl method."""
        # Test with file URL
        url = "https://example.com/path/to/file.html"
        self.assertEqual(SpiderFootHelpers.urlBaseUrl(url), "https://example.com")
        
        # Test with query parameters
        url = "https://example.com/path?param=value"
        self.assertEqual(SpiderFootHelpers.urlBaseUrl(url), "https://example.com")
        
        # Test with port
        url = "https://example.com:8080/path"
        self.assertEqual(SpiderFootHelpers.urlBaseUrl(url), "https://example.com:8080")
        
        # Test invalid inputs
        self.assertIsNone(SpiderFootHelpers.urlBaseUrl(None))
        self.assertIsNone(SpiderFootHelpers.urlBaseUrl(""))

    def test_extract_emails_from_text(self):
        """Test extractEmailsFromText method."""
        text = """
        Contact us at support@example.com or sales@example.com.
        Invalid email: @example.com
        Another invalid: user@
        """
        
        emails = SpiderFootHelpers.extractEmailsFromText(text)
        self.assertEqual(len(emails), 2)
        self.assertIn("support@example.com", emails)
        self.assertIn("sales@example.com", emails)
        
        # Test invalid input
        self.assertEqual(SpiderFootHelpers.extractEmailsFromText(None), [])
        self.assertEqual(SpiderFootHelpers.extractEmailsFromText(""), [])

    def test_extract_urls_from_text(self):
        """Test extractUrlsFromText method."""
        text = """
        Visit our website at https://example.com or http://subdomain.example.org/path.
        Invalid URL: https://
        """
        
        urls = SpiderFootHelpers.extractUrlsFromText(text)
        self.assertEqual(len(urls), 2)
        self.assertIn("https://example.com", urls)
        self.assertIn("http://subdomain.example.org/path", urls)
        
        # Test invalid input
        self.assertEqual(SpiderFootHelpers.extractUrlsFromText(None), [])
        self.assertEqual(SpiderFootHelpers.extractUrlsFromText(""), [])

    def test_valid_email(self):
        """Test validEmail method."""
        # Test valid emails
        self.assertTrue(SpiderFootHelpers.validEmail("user@example.com"))
        self.assertTrue(SpiderFootHelpers.validEmail("user.name@example.co.uk"))
        
        # Test invalid emails
        self.assertFalse(SpiderFootHelpers.validEmail(""))
        self.assertFalse(SpiderFootHelpers.validEmail(None))
        self.assertFalse(SpiderFootHelpers.validEmail("user@"))
        self.assertFalse(SpiderFootHelpers.validEmail("@example.com"))
        self.assertFalse(SpiderFootHelpers.validEmail("user@.com"))
        self.assertFalse(SpiderFootHelpers.validEmail("user@example."))
        self.assertFalse(SpiderFootHelpers.validEmail("user@example"))

    def test_sanitise_input(self):
        """Test sanitiseInput method."""
        # Test list input conversion to HTML entities
        input_list = ["<script>", "alert(1)", "<b>bold</b>"]
        expected = ["&lt;script&gt;", "alert(1)", "&lt;b&gt;bold&lt;/b&gt;"]
        self.assertEqual(SpiderFootHelpers.sanitiseInput(input_list), expected)
        
        # Test non-list input returns empty list
        self.assertEqual(SpiderFootHelpers.sanitiseInput("string"), [])
        self.assertEqual(SpiderFootHelpers.sanitiseInput(None), [])
        self.assertEqual(SpiderFootHelpers.sanitiseInput(123), [])

    def test_gen_scan_instance_id(self):
        """Test genScanInstanceId method."""
        # Test that a string is returned
        scan_id = SpiderFootHelpers.genScanInstanceId()
        self.assertIsInstance(scan_id, str)
        
        # Test uniqueness
        scan_id2 = SpiderFootHelpers.genScanInstanceId()
        self.assertNotEqual(scan_id, scan_id2)

    def test_ssl_der_to_pem(self):
        """Test sslDerToPem method."""
        # Create a mock DER certificate
        mock_der = b"CERTIFICATE DATA"
        
        # Mock the ssl.DER_cert_to_PEM_cert function
        with mock.patch("ssl.DER_cert_to_PEM_cert") as mock_convert:
            mock_convert.return_value = "-----BEGIN CERTIFICATE-----\nMIIFJDCCBAy\n-----END CERTIFICATE-----\n"
            result = SpiderFootHelpers.sslDerToPem(mock_der)
            mock_convert.assert_called_once_with(mock_der)
            self.assertTrue(result.startswith("-----BEGIN CERTIFICATE-----"))
        
        # Test invalid input
        with self.assertRaises(TypeError):
            SpiderFootHelpers.sslDerToPem("not_bytes")
        with self.assertRaises(TypeError):
            SpiderFootHelpers.sslDerToPem(None)

    def test_country_name_from_country_code(self):
        """Test countryNameFromCountryCode method."""
        # Test valid country code
        self.assertEqual(SpiderFootHelpers.countryNameFromCountryCode("US"), "United States")
        self.assertEqual(SpiderFootHelpers.countryNameFromCountryCode("GB"), "United Kingdom")
        
        # Test invalid country code
        self.assertIsNone(SpiderFootHelpers.countryNameFromCountryCode("ZZ"))
        self.assertIsNone(SpiderFootHelpers.countryNameFromCountryCode(""))
        self.assertIsNone(SpiderFootHelpers.countryNameFromCountryCode(None))


if __name__ == '__main__':
    unittest.main()
