"""Unit tests for spiderfoot.logconfig module."""

import unittest
from unittest import mock
import logging
import os
import tempfile

from spiderfoot.logconfig import (
    configure_root_logger, 
    get_module_logger, 
    setup_file_logging,
    get_log_paths,
    get_log_level_from_config,
    setup_scan_logger
)


class TestSpiderFootLogConfig(unittest.TestCase):
    """Test cases for SpiderFoot logging configuration."""

    def setUp(self):
        """Set up test case."""
        # Reset the root logger
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        root.setLevel(logging.WARNING)
        
        # Create temp directory for logs
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up after test case."""
        # Remove temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @mock.patch('logging.getLogger')
    def test_configure_root_logger(self, mock_get_logger):
        """Test configure_root_logger function."""
        mock_logger = mock.MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Test with debug=False
        configure_root_logger(debug=False)
        mock_logger.setLevel.assert_called_with(logging.INFO)
        
        # Test with debug=True
        configure_root_logger(debug=True)
        mock_logger.setLevel.assert_called_with(logging.DEBUG)

    @mock.patch('logging.getLogger')
    def test_get_module_logger(self, mock_get_logger):
        """Test get_module_logger function."""
        mock_logger = mock.MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Get module logger
        logger = get_module_logger("test_module")
        
        # Verify logger was created correctly
        mock_get_logger.assert_called_with("spiderfoot.test_module")
        self.assertEqual(logger, mock_logger)

    @mock.patch('logging.FileHandler')
    def test_setup_file_logging(self, mock_file_handler):
        """Test setup_file_logging function."""
        mock_handler = mock.MagicMock()
        mock_file_handler.return_value = mock_handler
        
        # Set up file logging
        setup_file_logging("/path/to/log.log", level=logging.DEBUG)
        
        # Verify handler was created and configured correctly
        mock_file_handler.assert_called_with("/path/to/log.log")
        mock_handler.setLevel.assert_called_with(logging.DEBUG)
        mock_handler.setFormatter.assert_called_once()
        
    @mock.patch('spiderfoot.SpiderFootHelpers.logPath')
    def test_get_log_paths(self, mock_log_path):
        """Test get_log_paths function."""
        mock_log_path.return_value = "/path/to/logs"
        
        # Get log paths
        paths = get_log_paths()
        
        # Verify paths
        self.assertEqual(paths['debug'], "/path/to/logs/spiderfoot.debug.log")
        self.assertEqual(paths['error'], "/path/to/logs/spiderfoot.error.log")
        self.assertEqual(paths['syslog'], "/path/to/logs/spiderfoot.syslog.log")
        
    def test_get_log_level_from_config(self):
        """Test get_log_level_from_config function."""
        # Test with debug=True
        config = {'_debug': True}
        self.assertEqual(get_log_level_from_config(config), logging.DEBUG)
        
        # Test with debug=False
        config = {'_debug': False}
        self.assertEqual(get_log_level_from_config(config), logging.INFO)
        
        # Test with no config
        self.assertEqual(get_log_level_from_config(None), logging.INFO)
        
    @mock.patch('logging.getLogger')
    def test_setup_scan_logger(self, mock_get_logger):
        """Test setup_scan_logger function."""
        mock_logger = mock.MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Set up scan logger
        logger = setup_scan_logger("SCAN123")
        
        # Verify logger was created and configured correctly
        mock_get_logger.assert_called_with("spiderfoot.scan.SCAN123")
        self.assertEqual(logger, mock_logger)
        
    def test_file_logging_integration(self):
        """Test file logging integration."""
        # Create a real log file
        log_file = os.path.join(self.temp_dir, "test.log")
        
        # Set up file logging
        setup_file_logging(log_file)
        
        # Get a logger and log something
        logger = logging.getLogger("spiderfoot.test")
        logger.setLevel(logging.DEBUG)
        logger.info("Test log message")
        
        # Verify log file was created and contains the message
        with open(log_file, 'r') as f:
            content = f.read()
            self.assertIn("Test log message", content)


if __name__ == '__main__':
    unittest.main()
