"""Unit tests for spiderfoot.error_handling module."""

import unittest
from unittest import mock
import sys
import traceback

from spiderfoot.error_handling import (
    SpiderFootError, 
    SpiderFootDatabaseError, 
    SpiderFootScanError, 
    SpiderFootConfigError,
    SpiderFootAPIError,
    handle_exception,
    error_handler,
    api_error_handler,
    database_error_handler,
    get_error_context
)


class TestSpiderFootErrorHandling(unittest.TestCase):
    """Test cases for SpiderFootErrorHandling module."""

    def test_error_classes(self):
        """Test error class hierarchy."""
        # Test base error class
        error = SpiderFootError("Test error")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Test error")
        
        # Test database error class
        db_error = SpiderFootDatabaseError("DB error")
        self.assertIsInstance(db_error, SpiderFootError)
        self.assertEqual(str(db_error), "DB error")
        
        # Test scan error class
        scan_error = SpiderFootScanError("Scan error")
        self.assertIsInstance(scan_error, SpiderFootError)
        self.assertEqual(str(scan_error), "Scan error")
        
        # Test config error class
        config_error = SpiderFootConfigError("Config error")
        self.assertIsInstance(config_error, SpiderFootError)
        self.assertEqual(str(config_error), "Config error")
        
        # Test API error class
        api_error = SpiderFootAPIError("API error")
        self.assertIsInstance(api_error, SpiderFootError)
        self.assertEqual(str(api_error), "API error")
        
    @mock.patch('spiderfoot.error_handling.get_module_logger')
    @mock.patch('sys.exit')
    def test_handle_exception_fatal(self, mock_exit, mock_get_logger):
        """Test handle_exception function with fatal=True."""
        mock_logger = mock.MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Create test exception
        exception = ValueError("Test error")
        
        # Call handle_exception with fatal=True
        handle_exception(exception, "test_module", fatal=True)
        
        # Verify logger was called correctly
        mock_get_logger.assert_called_with("test_module")
        mock_logger.critical.assert_called_once()
        self.assertIn("FATAL ERROR (ValueError): Test error", mock_logger.critical.call_args[0][0])
        
        # Verify exit was called
        mock_exit.assert_called_with(1)

    @mock.patch('spiderfoot.error_handling.get_module_logger')
    def test_handle_exception_non_fatal(self, mock_get_logger):
        """Test handle_exception function with fatal=False."""
        mock_logger = mock.MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Create test exception
        exception = ValueError("Test error")
        
        # Call handle_exception with fatal=False
        handle_exception(exception, "test_module", fatal=False)
        
        # Verify logger was called correctly
        mock_get_logger.assert_called_with("test_module")
        mock_logger.error.assert_called_once()
        self.assertIn("ERROR (ValueError): Test error", mock_logger.error.call_args[0][0])
        
    def test_error_handler_decorator_success(self):
        """Test error_handler decorator with successful function."""
        # Create a test function wrapped with error_handler
        @error_handler
        def test_function():
            return "success"
            
        # Call the function
        result = test_function()
        
        # Verify result
        self.assertEqual(result, "success")
        
    @mock.patch('spiderfoot.error_handling.handle_exception')
    def test_error_handler_decorator_failure(self, mock_handle_exception):
        """Test error_handler decorator with function that raises exception."""
        # Create a test function wrapped with error_handler
        @error_handler
        def test_function():
            raise ValueError("Test error")
            
        # Call the function
        with self.assertRaises(ValueError):
            test_function()
            
        # Verify handle_exception was called
        mock_handle_exception.assert_called_once()
        args, _ = mock_handle_exception.call_args
        self.assertIsInstance(args[0], ValueError)
        self.assertEqual(args[1], "test_function")
        
    def test_api_error_handler_decorator_success(self):
        """Test api_error_handler decorator with successful function."""
        # Create a test function wrapped with api_error_handler
        @api_error_handler
        def test_function():
            return {"success": True}
            
        # Call the function
        result = test_function()
        
        # Verify result
        self.assertEqual(result, {"success": True})
        
    @mock.patch('spiderfoot.error_handling.get_module_logger')
    def test_api_error_handler_decorator_failure(self, mock_get_logger):
        """Test api_error_handler decorator with function that raises exception."""
        mock_logger = mock.MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Create a test function wrapped with api_error_handler
        @api_error_handler
        def test_function():
            raise ValueError("API error")
            
        # Call the function
        result = test_function()
        
        # Verify result contains error information
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "API error")
        
        # Verify logger was called
        mock_logger.error.assert_called_once()
        
    def test_database_error_handler_decorator_success(self):
        """Test database_error_handler decorator with successful function."""
        # Create a test function wrapped with database_error_handler
        @database_error_handler
        def test_function():
            return "db success"
            
        # Call the function
        result = test_function()
        
        # Verify result
        self.assertEqual(result, "db success")
        
    @mock.patch('spiderfoot.error_handling.get_module_logger')
    def test_database_error_handler_decorator_failure(self, mock_get_logger):
        """Test database_error_handler decorator with function that raises exception."""
        mock_logger = mock.MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Create a test function wrapped with database_error_handler
        @database_error_handler
        def test_function():
            raise ValueError("DB error")
            
        # Call the function and expect a SpiderFootDatabaseError
        with self.assertRaises(SpiderFootDatabaseError) as context:
            test_function()
            
        # Verify exception message
        self.assertIn("Database operation failed: DB error", str(context.exception))
        
        # Verify logger was called
        mock_logger.error.assert_called_once()
        
    @mock.patch('sys.exc_info')
    def test_get_error_context_with_exception(self, mock_exc_info):
        """Test get_error_context function with exception information."""
        # Mock exception info
        exc_type = ValueError
        exc_value = ValueError("Test error")
        exc_traceback = mock.MagicMock()
        mock_exc_info.return_value = (exc_type, exc_value, exc_traceback)
        
        # Mock traceback.extract_tb
        tb_entry = mock.MagicMock()
        tb_entry.filename = "test_file.py"
        tb_entry.lineno = 42
        tb_entry.name = "test_function"
        
        with mock.patch('traceback.extract_tb', return_value=[tb_entry]):
            # Get error context
            context = get_error_context()
            
            # Verify context contains expected information
            self.assertIn("Exception Type: ValueError", context)
            self.assertIn("Exception Value: Test error", context)
            self.assertIn("File 'test_file.py', line 42, in test_function", context)
        
    @mock.patch('sys.exc_info')
    def test_get_error_context_without_exception(self, mock_exc_info):
        """Test get_error_context function without exception information."""
        # Mock no exception info
        mock_exc_info.return_value = (None, None, None)
        
        # Get error context
        context = get_error_context()
        
        # Verify default message
        self.assertEqual(context, "No exception information available")

    def test_error_chain(self):
        """Test chained error handling."""
        # Create a chain of errors
        try:
            try:
                try:
                    raise ValueError("Root error")
                except ValueError as e:
                    raise SpiderFootError("Level 1 error") from e
            except SpiderFootError as e:
                raise SpiderFootScanError("Level 2 error") from e
        except SpiderFootScanError as e:
            # Get the chain
            root_cause = e.__cause__
            level_1 = root_cause.__cause__
            
            # Verify chain
            self.assertIsInstance(e, SpiderFootScanError)
            self.assertEqual(str(e), "Level 2 error")
            self.assertIsInstance(root_cause, SpiderFootError)
            self.assertEqual(str(root_cause), "Level 1 error")
            self.assertIsInstance(level_1, ValueError)
            self.assertEqual(str(level_1), "Root error")
            
    def test_custom_error_context(self):
        """Test custom error context."""
        # Create custom context
        custom_context = {
            'scan_id': 'test-scan',
            'module': 'test-module',
            'target': 'example.com'
        }
        
        # Create error with context
        err = SpiderFootError("Test error with context")
        err.context = custom_context
        
        # Verify context
        self.assertEqual(err.context, custom_context)
        
    @mock.patch('spiderfoot.error_handling.get_module_logger')
    def test_handle_exception_with_context(self, mock_get_logger):
        """Test handle_exception function with error context."""
        mock_logger = mock.MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Create test exception with context
        exception = SpiderFootError("Test error")
        exception.context = {'scan_id': 'test-scan'}
        
        # Call handle_exception
        handle_exception(exception, "test_module", fatal=False)
        
        # Verify logger was called with context
        mock_get_logger.assert_called_with("test_module")
        mock_logger.error.assert_called_once()
        log_message = mock_logger.error.call_args[0][0]
        self.assertIn("ERROR (SpiderFootError): Test error", log_message)
        self.assertIn("scan_id: test-scan", log_message)


if __name__ == '__main__':
    unittest.main()
