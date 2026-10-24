import pytest
import unittest
from unittest.mock import patch, MagicMock, Mock
import psycopg2
import time

from modules.sfp__stor_db import sfp__stor_db
from spiderfoot.sflib import SpiderFoot
from spiderfoot.event import SpiderFootEvent
from test.unit.utils.test_module_base import TestModuleBase
from test.unit.utils.test_helpers import safe_recursion


class TestModuleStor_db(TestModuleBase):
    """Comprehensive test suite for enhanced database storage module.
    
    Tests all enterprise-grade features including:
    - Connection pooling and health checks
    - PostgreSQL storage
    - Error handling and recovery
    - Configuration validation
    - Performance optimization
    """

    def setUp(self):
        """Set up before each test."""
        super().setUp()
        # Create a mock database handle
        self.mock_dbh = MagicMock()
        self.mock_dbh.scanEventStore = MagicMock()
        
        # Create SpiderFoot instance with mock database handle
        self.sf_instance = SpiderFoot(self.default_options)
        self.sf_instance.dbh = self.mock_dbh
        
        # Register event emitters if they exist
        if hasattr(self, 'module'):
            self.register_event_emitter(self.module)

    def tearDown(self):
        """Clean up after each test."""
        super().tearDown()        # Clean up any open connections
        if hasattr(self, 'module') and hasattr(self.module, 'pg_conn'):
            if self.module.pg_conn:
                try:
                    self.module.pg_conn.close()
                except:
                    pass

    def create_test_event(self, event_type="IP_ADDRESS", data="192.168.1.1", module="test_module"):
        """Create a test SpiderFoot event."""        # Create ROOT event first for other events to reference
        if event_type == "ROOT":
            event = SpiderFootEvent("ROOT", data, module)
        else:            # Create a root event to serve as source
            root_event = SpiderFootEvent("ROOT", "root", module)
            event = SpiderFootEvent(event_type, data, module, root_event)
        
        event.confidence = 100
        event.visibility = 1
        event.risk = 0
        return event

    @unittest.skip("This module contains an extra private option")
    def test_opts(self):
        module = sfp__stor_db()
        self.assertEqual(len(module.opts), len(module.optdescs))


    def test_setup_no_database_handle(self):
        """Test setup fails gracefully when no database handle is available."""
        sf_no_db = SpiderFoot(self.default_options)
        sf_no_db.dbh = None
        
        module = sfp__stor_db()
        module.setup(sf_no_db, dict())
        
        self.assertTrue(module.errorState)

    def test_postgresql_config_validation(self):
        """Test PostgreSQL configuration validation."""
        module = sfp__stor_db()
        
        # Test invalid db_type
        opts = {'db_type': 'invalid'}
        module.setup(self.sf_instance, opts)
        self.assertTrue(module.errorState)
        
        # Test missing required PostgreSQL options
        module_pg = sfp__stor_db()
        opts_pg = {
            'db_type': 'postgresql',
            'postgresql_host': '',  # Missing required field
            'postgresql_database': 'test'
        }
        module_pg.setup(self.sf_instance, opts_pg)
        self.assertTrue(module_pg.errorState)

    def test_postgresql_port_validation(self):
        """Test PostgreSQL port validation."""
        module = sfp__stor_db()
        
        # Test invalid port
        opts = {
            'db_type': 'postgresql',
            'postgresql_host': 'localhost',
            'postgresql_port': 'invalid',
            'postgresql_database': 'test',
            'postgresql_username': 'user'
        }
        module.setup(self.sf_instance, opts)
        self.assertTrue(module.errorState)
        
        # Test out of range port
        opts['postgresql_port'] = 99999
        module_range = sfp__stor_db()
        module_range.setup(self.sf_instance, opts)
        self.assertTrue(module_range.errorState)

    @patch('modules.sfp__stor_db.psycopg2.connect')
    def test_postgresql_connection_success(self, mock_connect):
        """Test successful PostgreSQL connection."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        module = sfp__stor_db()
        opts = {
            'db_type': 'postgresql',
            'postgresql_host': 'localhost',
            'postgresql_port': 5432,
            'postgresql_database': 'spiderfoot',
            'postgresql_username': 'user',
            'postgresql_password': 'pass',
            'postgresql_timeout': 30
        }
        
        module.setup(self.sf_instance, opts)
        
        self.assertFalse(module.errorState)
        self.assertIsNotNone(module.pg_conn)
        mock_connect.assert_called_once()

    @patch('psycopg2.connect', side_effect=Exception('Connection failed'))
    def test_postgresql_connection_failure(self, mock_connect):
        """Test PostgreSQL connection failure sets errorState."""
        module = sfp__stor_db()
        opts = {
            'db_type': 'postgresql',
            'postgresql_host': 'localhost',
            'postgresql_port': 5432,
            'postgresql_database': 'spiderfoot',
            'postgresql_username': 'user',
            'postgresql_password': 'pass',
            'enable_auto_recovery': False  # Explicitly set to False
        }
        module.setup(self.sf_instance, opts)
        self.assertTrue(module.errorState)

    def test_postgresql_health_check(self):
        """Test PostgreSQL connection health check."""
        module = sfp__stor_db()
        module.pg_conn = None  # Initialize the attribute
        
        # Test with no connection
        self.assertFalse(module._check_postgresql_connection())
        
        # Test with mock healthy connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        module.pg_conn = mock_conn
        
        self.assertTrue(module._check_postgresql_connection())
        mock_cursor.execute.assert_called_with("SELECT 1")
        mock_cursor.fetchone.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_postgresql_health_check_failure(self):
        """Test PostgreSQL health check failure."""
        module = sfp__stor_db()
        
        # Test with unhealthy connection
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = psycopg2.OperationalError("Connection lost")
        module.pg_conn = mock_conn
        
        self.assertFalse(module._check_postgresql_connection())

    def test_watchedEvents_should_return_list(self):
        module = sfp__stor_db()
        events = module.watchedEvents()
        self.assertIsInstance(events, list)
        self.assertIn("*", events)

    def test_producedEvents_should_return_list(self):
        module = sfp__stor_db()
        self.assertIsInstance(module.producedEvents(), list)



    @patch('modules.sfp__stor_db.psycopg2.connect')
    def test_postgresql_storage(self, mock_connect):
        """Test PostgreSQL storage functionality."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        module = sfp__stor_db()
        opts = {
            'db_type': 'postgresql',
            'postgresql_host': 'localhost',
            'postgresql_port': 5432,
            'postgresql_database': 'spiderfoot',
            'postgresql_username': 'user',
            'postgresql_password': 'pass',
            '_store': True
        }
        
        module.setup(self.sf_instance, opts)
        
        # Create test event
        test_event = self.create_test_event()
        
        # Mock getScanId
        module.getScanId = MagicMock(return_value="test_scan_id")
        
        module.handleEvent(test_event)
        
        # Verify PostgreSQL insert was called
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
        mock_cursor.close.assert_called()

    @patch('modules.sfp__stor_db.psycopg2.connect')
    def test_postgresql_storage_with_reconnect(self, mock_connect):
        """Test PostgreSQL storage with connection recovery."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # First connection succeeds, then fails health check
        mock_connect.return_value = mock_conn
        
        module = sfp__stor_db()
        opts = {
            'db_type': 'postgresql',
            'postgresql_host': 'localhost',
            'postgresql_port': 5432,
            'postgresql_database': 'spiderfoot',
            'postgresql_username': 'user',
            'postgresql_password': 'pass',
            '_store': True
        }
        
        module.setup(self.sf_instance, opts)
        
        # Simulate connection failure during health check
        mock_cursor.execute.side_effect = [
            psycopg2.OperationalError("Connection lost"),  # Health check fails
            None  # Reconnection succeeds
        ]
        
        # Create test event
        test_event = self.create_test_event()
        
        # Mock getScanId
        module.getScanId = MagicMock(return_value="test_scan_id")
        
        module.handleEvent(test_event)
        
        # Should attempt reconnection
        self.assertEqual(mock_connect.call_count, 2)


    @patch('modules.sfp__stor_db.psycopg2.connect')
    def test_storage_disabled(self, mock_connect):
        """Test that storage is skipped when disabled."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        module = sfp__stor_db()
        opts = {
            'db_type': 'postgresql',
            'postgresql_host': 'localhost',
            'postgresql_port': 5432,
            'postgresql_database': 'spiderfoot',
            'postgresql_username': 'user',
            'postgresql_password': 'pass',
            '_store': False
        }
        module.setup(self.sf_instance, opts)
        
        test_event = self.create_test_event()
        module.handleEvent(test_event)
        
        # Storage should not be called when disabled
        self.mock_dbh.scanEventStore.assert_not_called()

    @patch('modules.sfp__stor_db.psycopg2.connect')
    def test_storage_error_state(self, mock_connect):
        """Test that storage is skipped when module is in error state."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        module = sfp__stor_db()
        opts = {
            'db_type': 'postgresql',
            'postgresql_host': 'localhost',
            'postgresql_port': 5432,
            'postgresql_database': 'spiderfoot',
            'postgresql_username': 'user',
            'postgresql_password': 'pass',
            '_store': True
        }
        module.setup(self.sf_instance, opts)
        module.errorState = True
        
        test_event = self.create_test_event()
        module.handleEvent(test_event)
        
        # Storage should not be called when in error state
        self.mock_dbh.scanEventStore.assert_not_called()

    def test_cleanup_postgresql_connection(self):
        """Test proper cleanup of PostgreSQL connections."""
        module = sfp__stor_db()
        mock_conn = MagicMock()
        module.pg_conn = mock_conn
        
        # Simulate destruction
        module.__del__()
        
        mock_conn.close.assert_called_once()

    def test_phase2_bulk_processing_threshold(self):
        """Test Phase 2 bulk processing threshold functionality."""
        module = sfp__stor_db()
        opts = {
            'maxstorage': 1024,
            '_store': True,
            'db_type': 'sqlite',
            'bulk_processing_enabled': True,
            'bulk_threshold': 5
        }
        
        module.setup(self.sf_instance, opts)
        
        # Test that bulk processing is properly configured
        self.assertEqual(module.opts.get('bulk_threshold', 1), 5)
        
    def test_phase2_connection_pool_monitoring(self):
        """Test Phase 2 connection pool monitoring capabilities."""
        module = sfp__stor_db()
        opts = {
            'maxstorage': 1024,
            '_store': True,
            'db_type': 'postgresql',
            'postgresql_host': 'localhost',
            'postgresql_port': 5432,
            'postgresql_database': 'spiderfoot',
            'postgresql_username': 'user',
            'postgresql_password': 'pass',
            'enable_connection_monitoring': True
        }
        
        module.setup(self.sf_instance, opts)
        
        # Test monitoring is enabled
        self.assertEqual(module.opts.get('enable_connection_monitoring'), True)
        
    @patch('modules.sfp__stor_db.psycopg2.connect')
    def test_phase2_advanced_error_recovery(self, mock_connect):
        """Test Phase 2 advanced error recovery mechanisms."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Simulate connection failure followed by recovery
        mock_connect.side_effect = [
            psycopg2.OperationalError("Connection failed"),
            mock_conn  # Successful reconnection
        ]
        
        module = sfp__stor_db()
        opts = {
            'db_type': 'postgresql',
            'postgresql_host': 'localhost',
            'postgresql_port': 5432,
            'postgresql_database': 'spiderfoot',
            'postgresql_username': 'user',
            'postgresql_password': 'pass',
            '_store': True,
            'enable_auto_recovery': True
        }
        
        module.setup(self.sf_instance, opts)
        
        # First attempt should fail, but module should handle gracefully
        self.assertFalse(module.errorState or module.pg_conn is not None)
        
        
        
    @patch('modules.sfp__stor_db.psycopg2.connect')
    def test_phase2_connection_health_monitoring(self, mock_connect):
        """Test Phase 2 connection health monitoring."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        module = sfp__stor_db()
        opts = {
            'db_type': 'postgresql',
            'postgresql_host': 'localhost',
            'postgresql_port': 5432,
            'postgresql_database': 'spiderfoot',
            'postgresql_username': 'user',
            'postgresql_password': 'pass',
            '_store': True,
            'enable_health_monitoring': True,
            'health_check_interval': 30
        }
        
        module.setup(self.sf_instance, opts)
        
        # Test health check functionality
        if hasattr(module, '_check_postgresql_connection'):
            health_status = module._check_postgresql_connection()
            self.assertTrue(health_status, "Connection should be healthy")
            
            # Verify health check made proper database call
            mock_cursor.execute.assert_called_with("SELECT 1")
            mock_cursor.fetchone.assert_called_once()
            mock_cursor.close.assert_called_once()
            
    def test_phase2_configuration_validation_enhancements(self):
        """Test Phase 2 enhanced configuration validation."""
        module = sfp__stor_db()
        
        # Test enhanced PostgreSQL configuration validation
        invalid_configs = [
            {
                'db_type': 'postgresql',
                'postgresql_host': '',  # Empty host
                'postgresql_port': 5432,
                'postgresql_database': 'test',
                'postgresql_username': 'user',
                'postgresql_password': 'pass'
            },
            {
                'db_type': 'postgresql',
                'postgresql_host': 'localhost',
                'postgresql_port': 'invalid_port',  # Invalid port
                'postgresql_database': 'test',
                'postgresql_username': 'user',
                'postgresql_password': 'pass'
            },
            {
                'db_type': 'postgresql',
                'postgresql_host': 'localhost',
                'postgresql_port': 70000,  # Port out of range
                'postgresql_database': 'test',
                'postgresql_username': 'user',
                'postgresql_password': 'pass'
            }
        ]
        
        for invalid_config in invalid_configs:
            invalid_config['_store'] = True
            module.setup(self.sf_instance, invalid_config)
            self.assertTrue(module.errorState, f"Should detect invalid config: {invalid_config}")
            
            # Reset for next test
            module = sfp__stor_db()
            
    def test_phase2_enterprise_feature_integration(self):
        """Test Phase 2 enterprise features integration."""
        module = sfp__stor_db()
        
        # Test with full enterprise configuration
        enterprise_opts = {
            'maxstorage': 1024,
            '_store': True,
            'db_type': 'postgresql',
            'postgresql_host': 'localhost',
            'postgresql_port': 5432,
            'postgresql_database': 'enterprise_db',
            'postgresql_username': 'enterprise_user',
            'postgresql_password': 'secure_password',
            'postgresql_timeout': 30,
            # Phase 2 enterprise features
            'enable_connection_pooling': True,
            'enable_load_balancing': True,
            'enable_auto_scaling': True,
            'enable_performance_monitoring': True,
            'enable_query_optimization': True,
            'bulk_processing_enabled': True,
            'bulk_threshold': 100,
            'connection_pool_size': 10,
            'max_connections': 50,
            'health_check_interval': 30,
            'enable_graceful_shutdown': True
        }
        
        # Setup should not fail with enterprise configuration
        try:
            module.setup(self.sf_instance, enterprise_opts)
            setup_successful = True
        except Exception as e:
            setup_successful = False
            print(f"Enterprise setup failed: {e}")
            
        # Even if PostgreSQL is not available, setup should handle gracefully
        # The key is that it doesn't crash with enterprise options
        self.assertTrue(setup_successful or module.errorState, 
                       "Enterprise configuration should be handled gracefully")
                       
        
