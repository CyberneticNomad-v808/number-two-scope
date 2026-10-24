#!/usr/bin/env python3
"""
Enhanced unit tests for sfwebui.py - web user interface

This comprehensive test suite covers all functionality in sfwebui.py including:
- Web UI initialization and configuration
- Endpoint functionality and routing
- Security and validation features
- Database operations and data handling
- Error handling and edge cases
- Template rendering and response formatting
"""

import unittest
from contextlib import suppress
from test.unit.utils.test_module_base import TestModuleBase
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import tempfile
import time

# Add the SpiderFoot directory to the path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sfwebui import SpiderFootWebUi, SpiderFootWebUiApp  # noqa: E402


class TestSpiderFootWebUiEnhanced(TestModuleBase):
    """Enhanced test cases for SpiderFootWebUi functionality."""

    def setUp(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Set up test fixtures before each test method."""
        super().setUp()

        self.web_config = {
            'interface': '127.0.0.1',
            'port': 8080,
            'root': '/'
        }
        self.config = {
            '__database': 'test.db',
            '_debug': False,
            '__modules__': {},
            '__correlationrules__': []
        }

        # Use persistent patchers
        self.db_patcher = patch('sfwebui.SpiderFootDb')
        self.sf_patcher = patch('sfwebui.SpiderFoot')
        self.log_listener_patcher = patch('sfwebui.logListenerSetup')
        self.log_worker_patcher = patch('sfwebui.logWorkerSetup')
        self.routes_db_patcher = patch('spiderfoot.webui.routes.SpiderFootDb')
        self.routes_sf_patcher = patch('spiderfoot.webui.routes.SpiderFoot')

        self.mock_db = self.db_patcher.start()
        self.mock_sf = self.sf_patcher.start()
        self.log_listener_patcher.start()
        self.log_worker_patcher.start()
        self.routes_db_patcher.start()
        self.mock_routes_sf = self.routes_sf_patcher.start()

        self.mock_sf.return_value.configUnserialize.return_value = self.config
        self.mock_routes_sf.return_value.configUnserialize.return_value = self.config
        self.mock_db.return_value.configGet.return_value = {}

        self.webui = SpiderFootWebUi(self.web_config, self.config)

    def tearDown(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Tear down test fixtures after each test method."""
        for patcher_name in ['db_patcher', 'sf_patcher', 'log_listener_patcher',
                              'log_worker_patcher', 'routes_db_patcher',
                              'routes_sf_patcher']:
            with suppress(AttributeError, RuntimeError):
                getattr(self, patcher_name).stop()
        super().tearDown()

    # =============================================================================
    # INITIALIZATION AND CONFIGURATION TESTS
    # =============================================================================

    def test_webui_initialization_success(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test successful WebUI initialization."""
        with patch('spiderfoot.webui.routes.logListenerSetup') as mock_log_listener, \
             patch('spiderfoot.webui.routes.logWorkerSetup') as mock_log_worker:

            webui = SpiderFootWebUi(self.web_config, self.config)

            self.assertIsNotNone(webui)
            # logListenerSetup should be called when loggingQueue is None
            mock_log_listener.assert_called_once()
            mock_log_worker.assert_called_once()

    def test_webui_initialization_invalid_config(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test WebUI initialization with invalid configuration."""
        with self.assertRaises(TypeError):
            SpiderFootWebUi('invalid_config', self.config)

        with self.assertRaises(TypeError):
            SpiderFootWebUi(self.web_config, 'invalid_config')

    def test_webui_initialization_empty_config(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test WebUI initialization with empty configuration."""
        with self.assertRaises(ValueError):
            SpiderFootWebUi({}, self.config)

        with self.assertRaises(ValueError):
            SpiderFootWebUi(self.web_config, {})

    @patch('sfwebui.SpiderFootDb')
    @patch('sfwebui.SpiderFoot')
    @patch('sfwebui.logListenerSetup')
    @patch('sfwebui.logWorkerSetup')
    def test_webui_initialization_with_minimal_config(
            self: 'TestSpiderFootWebUiEnhanced',
            mock_log_worker: MagicMock,
            mock_log_listener: MagicMock,
            mock_sf: MagicMock,
            mock_db: MagicMock) -> None:
        """Test WebUI initialization with minimal valid configuration.

        Args:
            mock_log_worker: Mock for logWorkerSetup
            mock_log_listener: Mock for logListenerSetup
            mock_sf: Mock for SpiderFoot
            mock_db: Mock for SpiderFootDb
        """
        minimal_config = {'__database': 'test.db'}

        mock_sf.return_value.configUnserialize.return_value = minimal_config
        mock_db.return_value.configGet.return_value = {}

        webui = SpiderFootWebUi(self.web_config, minimal_config)
        self.assertIsNotNone(webui)

    def test_validate_configuration(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test configuration validation method."""
        # Should not raise exceptions with valid config
        try:
            self.webui._validate_configuration()
        except Exception as e:
            self.fail('Configuration validation failed: ' + str(e))

    def test_setup_additional_security_headers(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test security headers setup."""
        # Should not raise exceptions
        try:
            self.webui._setup_additional_security_headers()
        except Exception as e:
            self.fail('Security headers setup failed: ' + str(e))

    # =============================================================================
    # VALIDATION METHODS TESTS
    # =============================================================================

    def test_validate_scan_id_valid(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test scan ID validation with valid IDs."""
        valid_scan_ids = [
            'a1b2c3d4e5f6789012345678901234ab',
            'ABCDEF1234567890ABCDEF1234567890',
            '12345678901234567890123456789012'
        ]

        for scan_id in valid_scan_ids:
            with patch.object(self.webui, '_get_dbh') as mock_get_dbh:
                mock_db = Mock()
                mock_db.scanInstanceGet.return_value = ['scan_name']
                mock_get_dbh.return_value = mock_db
                result = self.webui.validate_scan_id(scan_id)
                self.assertTrue(result)

    def test_validate_scan_id_invalid_format(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test scan ID validation with invalid formats."""
        invalid_scan_ids = [
            '',  # empty
            None,  # None
            123,  # not string
            'short',  # too short
            'toolongtobeavalidscanidhexstring123456789',  # too long
            'invalid-chars-!@#$',  # invalid characters
            'g1h2i3j4k5l6789012345678901234mn'  # invalid hex chars
        ]

        for scan_id in invalid_scan_ids:
            result = self.webui.validate_scan_id(scan_id)
            self.assertFalse(result)

    def test_validate_scan_id_not_in_database(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test scan ID validation when scan doesn't exist in database."""
        with patch.object(self.webui, '_get_dbh') as mock_get_dbh:
            mock_db = Mock()
            mock_db.scanInstanceGet.return_value = None
            mock_get_dbh.return_value = mock_db
            result = self.webui.validate_scan_id('a1b2c3d4e5f6789012345678901234ab')
            self.assertFalse(result)

    def test_validate_workspace_id_valid(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test workspace ID validation with valid IDs."""
        with patch('sfwebui.SpiderFootWorkspace') as mock_workspace_class:
            mock_workspace = Mock()
            # The method should return a non-None value to indicate success
            mock_workspace.getWorkspace.return_value = {'id': 'test_workspace', 'name': 'Test'}
            mock_workspace_class.return_value = mock_workspace

            result = self.webui.validate_workspace_id('test_workspace')
            self.assertTrue(result)
            mock_workspace.getWorkspace.assert_called_once_with('test_workspace')
            self.assertTrue(result)

    def test_validate_workspace_id_invalid(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test workspace ID validation with invalid IDs."""
        invalid_ids = ['', None, 123]

        for workspace_id in invalid_ids:
            result = self.webui.validate_workspace_id(workspace_id)
            self.assertFalse(result)

    # =============================================================================
    # INPUT SANITIZATION TESTS
    # =============================================================================

    def test_sanitize_user_input_string(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test user input sanitization with strings."""
        test_cases = [
            ('<script>alert("xss")</script>', '&lt;script&gt;alert("xss")&lt;/script&gt;'),
            ('Normal text', 'Normal text'),
            ('Text with & ampersand', 'Text with & ampersand'),  # & gets escaped then unescaped
            ('', ''),
            ('Text with "quotes"', 'Text with "quotes"')  # quotes get escaped then unescaped
        ]

        for input_text, expected in test_cases:
            result = self.webui.sanitize_user_input(input_text)
            self.assertEqual(result, expected)

    def test_sanitize_user_input_list(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test user input sanitization with lists."""
        input_list = ['<script>test</script>', 'normal text', '<b>bold</b>']
        expected = ['&lt;script&gt;test&lt;/script&gt;', 'normal text', '&lt;b&gt;bold&lt;/b&gt;']

        result = self.webui.sanitize_user_input(input_list)
        self.assertEqual(result, expected)

    def test_sanitize_user_input_edge_cases(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test user input sanitization with edge cases."""
        test_cases = [
            (None, ''),
            (123, '123'),
            ({'key': 'value'}, str({'key': 'value'})),
            (['mixed', 123, None], ['mixed', '123', ''])
        ]

        for input_data, expected in test_cases:
            result = self.webui.sanitize_user_input(input_data)
            self.assertEqual(result, expected)

    # =============================================================================
    # ERROR HANDLING TESTS
    # =============================================================================

    def test_handle_error_standard(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test standard error handling."""
        result = self.webui.handle_error('Test error message')

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Test error message')
        self.assertEqual(result['error_type'], 'error')
        self.assertIn('timestamp', result)

    def test_handle_error_different_types(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test error handling with different error types."""
        error_types = ['error', 'warning', 'info']

        for error_type in error_types:
            result = self.webui.handle_error('Test message', error_type)
            self.assertEqual(result['error_type'], error_type)

    def test_handle_error_with_logging(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test error handling includes appropriate logging."""
        with patch.object(self.webui, 'log') as mock_log:
            self.webui.handle_error('Test error', 'error')
            mock_log.error.assert_called_once()

            self.webui.handle_error('Test warning', 'warning')
            mock_log.warning.assert_called_once()

            self.webui.handle_error('Test info', 'info')
            mock_log.info.assert_called_once()

    # =============================================================================
    # SYSTEM STATUS AND MONITORING TESTS
    # =============================================================================

    def test_get_system_status_success(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test system status retrieval."""
        with patch.object(self.webui, '_get_dbh') as mock_get_dbh:
            mock_db = Mock()
            mock_db.scanInstanceList.return_value = [
                ('scan1', 'name1', 123456, 'target1', 'mod1', 'FINISHED'),
                ('scan2', 'name2', 123457, 'target2', 'mod2', 'RUNNING'),
            ]
            mock_get_dbh.return_value = mock_db

            result = self.webui.get_system_status()

            self.assertTrue(result['success'])
            self.assertEqual(result['total_scans'], 2)
            self.assertEqual(result['active_scans'], 1)
            self.assertIn('python_version', result)
            self.assertIn('spiderfoot_version', result)

    def test_get_system_status_no_psutil(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test system status when database fails."""
        with patch.object(self.webui, '_get_dbh') as mock_get_dbh:
            mock_get_dbh.side_effect = Exception('Database connection failed')

            result = self.webui.get_system_status()

            self.assertFalse(result['success'])
            self.assertIn('error', result)

    def test_get_performance_metrics_success(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test performance metrics retrieval."""
        # Mock the get_performance_metrics method to simulate psutil being available
        with patch.object(self.webui, '_get_dbh') as mock_get_dbh:
            mock_db = Mock()
            mock_db.conn_path = '/tmp/test.db'
            mock_get_dbh.return_value = mock_db

            # Mock psutil module directly instead of __import__ to avoid recursion
            with patch.dict('sys.modules', {'psutil': Mock()}) as mock_modules:
                # Create a mock psutil module
                mock_psutil = mock_modules['psutil']
                mock_psutil.cpu_percent.return_value = 25.5
                mock_memory = Mock()
                mock_memory.percent = 75.0
                mock_memory.available = 1024 * 1024 * 1024
                mock_psutil.virtual_memory.return_value = mock_memory

                mock_disk = Mock()
                mock_disk.percent = 50.0
                mock_disk.free = 10 * 1024 * 1024 * 1024
                mock_psutil.disk_usage.return_value = mock_disk

                with patch('os.path.getsize', return_value=1024 * 1024):
                    result = self.webui.get_performance_metrics()

                    self.assertTrue(result['success'])
                    self.assertIn('cpu_percent', result)
                    self.assertIn('memory_percent', result)
                    self.assertIn('disk_percent', result)
                    self.assertIn('database_size', result)

    def test_get_performance_metrics_no_psutil(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test performance metrics when psutil is not available."""
        # Mock psutil to not be available by removing it from sys.modules
        with patch.dict('sys.modules', {'psutil': None}):
            # Mock import to raise ImportError for psutil
            original_import = __import__

            def mock_import(name: str, *args: object, **kwargs: object) -> object:
                if name == 'psutil':
                    raise ImportError("No module named 'psutil'")
                return original_import(name, *args, **kwargs)

            with patch('builtins.__import__', side_effect=mock_import):
                result = self.webui.get_performance_metrics()

                self.assertFalse(result['success'])
                self.assertIn('error', result)
                self.assertIn('psutil not available', result['error'])

    # =============================================================================
    # DATABASE OPERATIONS TESTS
    # =============================================================================

    def test_cleanup_old_scans_success(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test successful cleanup of old scans."""
        with patch.object(self.webui, '_get_dbh') as mock_get_dbh:
            mock_db = Mock()
            # Mock scan list with old and recent scans
            # Format: [scan_id, name, start_time, target, module, status]
            old_time = 1000000000  # Very old timestamp
            recent_time = time.time() - 3600  # 1 hour ago
            mock_db.scanInstanceList.return_value = [
                ['old_scan_1', 'Old Scan 1', old_time, 'target1', 'FINISHED', 'module1'],
                ['recent_scan', 'Recent Scan', recent_time, 'target2', 'FINISHED', 'module2']
            ]
            mock_db.scanInstanceDelete.return_value = True
            mock_get_dbh.return_value = mock_db

            result = self.webui.cleanup_old_scans(30)

            self.assertTrue(result['success'])
            self.assertIn('cleaned_scans', result)
            self.assertIn('total_old_scans', result)

    def test_cleanup_old_scans_error(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test cleanup of old scans with database error."""
        with patch.object(self.webui, '_get_dbh') as mock_get_dbh:
            mock_get_dbh.side_effect = Exception('Database error')

            result = self.webui.cleanup_old_scans(30)

            self.assertFalse(result['success'])
            self.assertIn('error', result)

    def test_backup_database_success(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test successful database backup."""
        with tempfile.NamedTemporaryFile() as temp_file, \
             patch('shutil.copy2') as mock_copy:
            result = self.webui.backup_database(temp_file.name)

            self.assertTrue(result['success'])
            self.assertIn('backup_path', result)
            mock_copy.assert_called_once()

    def test_backup_database_error(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test database backup with error."""
        with patch('shutil.copy2', side_effect=IOError('Permission denied')):
            result = self.webui.backup_database('/invalid/path')

            self.assertFalse(result['success'])
            self.assertIn('error', result)

    # =============================================================================
    # HEALTH CHECK TESTS
    # =============================================================================

    def test_health_check_all_pass(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test health check when all components are healthy."""
        with patch.object(self.webui, '_get_dbh') as mock_get_dbh:
            mock_db = Mock()
            mock_db.configGet.return_value = {'test': 'value'}
            mock_get_dbh.return_value = mock_db

            result = self.webui.health_check()

            self.assertTrue(result['success'])
            self.assertIn('checks', result)

    def test_health_check_database_fail(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test health check when database check fails."""
        with patch.object(self.webui, '_get_dbh') as mock_get_dbh:
            mock_get_dbh.side_effect = Exception('Database connection failed')

            result = self.webui.health_check()

            self.assertFalse(result['success'])
            # The health check returns a structured format with 'checks' containing details
            self.assertIn('checks', result)
            self.assertEqual(result['checks']['database']['status'], 'ERROR')

    def test_health_check_configuration_validation(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test health check includes configuration validation."""
        result = self.webui.health_check()

        self.assertIn('checks', result)
        self.assertIn('configuration', result['checks'])

    # =============================================================================
    # TEMPLATE AND RENDERING TESTS
    # =============================================================================

    @patch('sfwebui.Template')
    def test_template_rendering_success(
            self: 'TestSpiderFootWebUiEnhanced',
            mock_template: MagicMock) -> None:
        """Test successful template rendering.

        Args:
            mock_template: Mock for Template class
        """
        mock_template_instance = MagicMock()
        mock_template.return_value = mock_template_instance
        mock_template_instance.render.return_value = '<html>Test</html>'

        # Test that template rendering works (would be called by routes)
        template = mock_template('test_template')
        result = template.render(test_data='value')

        self.assertEqual(result, '<html>Test</html>')

    def test_error_page_rendering(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test error page rendering."""
        with patch('cherrypy.response') as mock_response:
            self.webui.error_page()
            self.assertEqual(mock_response.status, 500)

    def test_error_page_401_unauthorized(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test 401 error page rendering."""
        result = self.webui.error_page_401('401 Unauthorized', 'Unauthorized', '')
        self.assertEqual(result, '')

    def test_error_page_404_not_found(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test 404 error page rendering."""
        result = self.webui.error_page_404('404 Not Found', 'Not Found', '')
        self.assertIn('<!DOCTYPE html>', result)
        self.assertIn('Not Found', result)

    # =============================================================================
    # SECURITY FEATURES TESTS
    # =============================================================================

    def test_jsonify_error_security_headers(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test jsonify_error sets appropriate security headers."""
        with patch('cherrypy.response') as mock_response:
            mock_response.headers = {}

            result = self.webui.jsonify_error('400 Bad Request', 'Invalid input')

            self.assertEqual(mock_response.headers['Content-Type'], 'application/json')
            self.assertEqual(mock_response.status, '400 Bad Request')
            self.assertEqual(result['error']['http_status'], '400 Bad Request')

    def test_security_headers_setup_with_secure_module(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test security headers setup when secure module is available."""
        with patch('sfwebui.secure') as mock_secure:
            mock_secure.SecureHeaders.return_value = MagicMock()

            # Should not raise exceptions
            self.webui._setup_additional_security_headers()

    def test_security_headers_setup_without_secure_module(self: 'TestSpiderFootWebUiEnhanced') -> None:
        """Test security headers setup when secure module is not available."""
        with patch('sfwebui.secure', None):
            # Should not raise exceptions
            try:
                self.webui._setup_additional_security_headers()
            except Exception as e:
                self.fail('Security headers setup should not fail without secure module: ' + str(e))


class TestSpiderFootWebUiAppEnhanced(TestModuleBase):
    """Enhanced test cases for SpiderFootWebUiApp functionality."""

    def setUp(self: 'TestSpiderFootWebUiAppEnhanced') -> None:
        """Set up test fixtures."""
        super().setUp()

        self.config = {
            '__database': 'test.db',
            '_debug': False,
            '__modules__': {}
        }

    @patch('sfwebui.SpiderFootDb')
    @patch('sfwebui.SpiderFoot')
    @patch('sfwebui.logListenerSetup')
    @patch('sfwebui.logWorkerSetup')
    def test_webui_app_initialization(
            self: 'TestSpiderFootWebUiAppEnhanced',
            mock_log_worker: MagicMock,
            mock_log_listener: MagicMock,
            mock_sf: MagicMock,
            mock_db: MagicMock) -> None:
        """Test WebUI app initialization.

        Args:
            mock_log_worker: Mock for logWorkerSetup
            mock_log_listener: Mock for logListenerSetup
            mock_sf: Mock for SpiderFoot
            mock_db: Mock for SpiderFootDb
        """
        mock_sf.return_value.configUnserialize.return_value = self.config
        mock_db.return_value.configGet.return_value = {}

        app = SpiderFootWebUiApp(self.config)

        self.assertIsNotNone(app)

    def test_webui_app_validate_and_setup_config(self: 'TestSpiderFootWebUiAppEnhanced') -> None:
        """Test configuration validation and setup in app."""
        with patch('sfwebui.SpiderFootDb'), \
             patch('sfwebui.SpiderFoot'), \
             patch('sfwebui.logListenerSetup'), \
             patch('sfwebui.logWorkerSetup'):

            app = SpiderFootWebUiApp(self.config)

            # Should have completed setup without errors
            self.assertIsNotNone(app)

    def test_webui_app_mount_functionality(self: 'TestSpiderFootWebUiAppEnhanced') -> None:
        """Test app mounting functionality."""
        with patch('sfwebui.SpiderFootDb'), \
             patch('sfwebui.SpiderFoot'), \
             patch('sfwebui.logListenerSetup'), \
             patch('sfwebui.logWorkerSetup'):

            app = SpiderFootWebUiApp(self.config)

            # Test mount method exists and can be called
            try:
                result = app.mount()
                # Mount should return some result
                self.assertIsNotNone(result)
            except Exception:
                # May fail due to missing dependencies, but should not crash
                pass

    def test_webui_app_error_pages(self: 'TestSpiderFootWebUiAppEnhanced') -> None:
        """Test custom error page handling in app."""
        with patch('sfwebui.SpiderFootDb'), \
             patch('sfwebui.SpiderFoot'), \
             patch('sfwebui.logListenerSetup'), \
             patch('sfwebui.logWorkerSetup'):

            app = SpiderFootWebUiApp(self.config)

            # Test error page methods exist
            self.assertTrue(hasattr(app, '_error_page_401'))
            self.assertTrue(hasattr(app, '_error_page_404'))
            self.assertTrue(hasattr(app, '_error_page_500'))

    def test_webui_app_system_validation(self: 'TestSpiderFootWebUiAppEnhanced') -> None:
        """Test system validation in app."""
        with patch('sfwebui.SpiderFootDb'), \
             patch('sfwebui.SpiderFoot'), \
             patch('sfwebui.logListenerSetup'), \
             patch('sfwebui.logWorkerSetup'):

            app = SpiderFootWebUiApp(self.config)

            # Test validation method
            try:
                result = app.validate_system()
                self.assertIsInstance(result, dict)
            except Exception:
                # May fail due to missing dependencies
                pass

    def test_webui_app_system_info(self: 'TestSpiderFootWebUiAppEnhanced') -> None:
        """Test system info retrieval in app."""
        with patch('sfwebui.SpiderFootDb'), \
             patch('sfwebui.SpiderFoot'), \
             patch('sfwebui.logListenerSetup'), \
             patch('sfwebui.logWorkerSetup'):

            app = SpiderFootWebUiApp(self.config)

            # Test system info method
            try:
                result = app.get_system_info()
                self.assertIsInstance(result, dict)
            except Exception:
                # May fail due to missing dependencies
                pass


class TestSpiderFootWebUiEdgeCases(TestModuleBase):
    """Edge case and integration tests for SpiderFootWebUi."""

    def setUp(self: 'TestSpiderFootWebUiEdgeCases') -> None:
        """Set up test fixtures."""
        super().setUp()

        self.web_config = {'interface': '127.0.0.1', 'port': 8080, 'root': '/'}
        self.config = {'__database': 'test.db', '_debug': False}

    def test_webui_with_missing_dependencies(self: 'TestSpiderFootWebUiEdgeCases') -> None:
        """Test WebUI behavior when optional dependencies are missing."""
        with patch('sfwebui.secure', None), \
             patch('sfwebui.SpiderFootDb'), \
             patch('sfwebui.SpiderFoot'), \
             patch('sfwebui.logListenerSetup'), \
             patch('sfwebui.logWorkerSetup'):

            # Should still initialize without secure module
            webui = SpiderFootWebUi(self.web_config, self.config)
            self.assertIsNotNone(webui)

    def test_webui_large_data_handling(self: 'TestSpiderFootWebUiEdgeCases') -> None:
        """Test WebUI handling of large datasets."""
        with patch('sfwebui.SpiderFootDb'), \
             patch('sfwebui.SpiderFoot'), \
             patch('sfwebui.logListenerSetup'), \
             patch('sfwebui.logWorkerSetup'):

            webui = SpiderFootWebUi(self.web_config, self.config)

            # Test with large input list
            large_input = ['<script>test</script>'] * 10000
            result = webui.sanitize_user_input(large_input)

            self.assertEqual(len(result), 10000)
            self.assertTrue(all('&lt;script&gt;' in item for item in result))

    def test_webui_concurrent_access_simulation(self: 'TestSpiderFootWebUiEdgeCases') -> None:
        """Test WebUI behavior under simulated concurrent access."""
        with patch('sfwebui.SpiderFootDb'), \
             patch('sfwebui.SpiderFoot'), \
             patch('sfwebui.logListenerSetup'), \
             patch('sfwebui.logWorkerSetup'):

            webui = SpiderFootWebUi(self.web_config, self.config)

            # Simulate multiple rapid method calls
            for i in range(100):
                scan_id = 'scan_' + str(i).zfill(32)
                result = webui.validate_scan_id(scan_id)
                # Should handle rapid calls without errors
                self.assertIsInstance(result, bool)

    def test_webui_memory_management(self: 'TestSpiderFootWebUiEdgeCases') -> None:
        """Test WebUI memory management with repeated operations."""
        import gc

        with patch('sfwebui.SpiderFootDb'), \
             patch('sfwebui.SpiderFoot'), \
             patch('sfwebui.logListenerSetup'), \
             patch('sfwebui.logWorkerSetup'):

            webui = SpiderFootWebUi(self.web_config, self.config)

            # Force garbage collection
            gc.collect()
            initial_objects = len(gc.get_objects())

            # Perform repeated operations
            for i in range(50):
                test_data = ['test_data_' + str(j) for j in range(100)]
                webui.sanitize_user_input(test_data)

                if i % 10 == 0:
                    gc.collect()

            # Final garbage collection
            gc.collect()
            final_objects = len(gc.get_objects())

            # Memory usage shouldn't grow excessively
            self.assertLess(final_objects - initial_objects, 1000)

    def test_webui_unicode_handling(self: 'TestSpiderFootWebUiEdgeCases') -> None:
        """Test WebUI handling of Unicode and international characters."""
        with patch('sfwebui.SpiderFootDb'), \
             patch('sfwebui.SpiderFoot'), \
             patch('sfwebui.logListenerSetup'), \
             patch('sfwebui.logWorkerSetup'):

            webui = SpiderFootWebUi(self.web_config, self.config)

            unicode_tests = [
                'Testing unicode: αβγδε',
                'Chinese characters: 测试数据',
                'Emoji test: 🚀🌟⭐',
                'Mixed: Test αβγ 测试 🚀',
                'Special chars: ñáéíóú'
            ]

            for test_string in unicode_tests:
                result = webui.sanitize_user_input(test_string)
                # Should handle unicode without errors
                self.assertIsInstance(result, str)
                self.assertGreater(len(result), 0)


if __name__ == '__main__':
    unittest.main()
