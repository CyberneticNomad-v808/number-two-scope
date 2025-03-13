"""Unit tests for sfscan.py."""

import unittest
from unittest import mock
import multiprocessing as mp
import queue
import time
import os
import sys

# Mock modules to avoid importing real ones in testing
sys.modules['sflib'] = mock.MagicMock()
sys.modules['spiderfoot'] = mock.MagicMock()

# Now we can import from sfscan
from sfscan import SpiderFootScanner, startSpiderFootScanner


class TestSpiderFootScanner(unittest.TestCase):
    """Test cases for SpiderFootScanner class."""
    
    def setUp(self):
        """Set up test case."""
        # Mock configuration
        self.config = {
            '_debug': False,
            '_maxthreads': 3,
            '__modules__': {
                'sfp_test1': {
                    'provides': ['IP_ADDRESS'],
                    'meta': {'flags': ['passive']},
                    'opts': {}
                },
                'sfp_test2': {
                    'provides': ['DOMAIN_NAME'],
                    'meta': {'flags': ['passive']},
                    'opts': {}
                }
            }
        }
        
        # Create logging queue
        self.loggingQueue = mp.Queue()
        
        # Create mock database
        self.dbh = mock.MagicMock()
        
        # Set up scanner params
        self.scanName = "Test Scan"
        self.scanId = "test-scan-id"
        self.scanTarget = "example.com"
        self.targetType = "INTERNET_NAME"
        self.moduleList = ["sfp_test1", "sfp_test2"]
        
        # Patch importlib.import_module to return mock modules
        self.import_module_patcher = mock.patch('importlib.import_module')
        self.mock_import_module = self.import_module_patcher.start()
        
        # Mock module classes
        self.mock_modules = {}
        for module_name in self.moduleList:
            mock_module = mock.MagicMock()
            mock_module_class = mock.MagicMock()
            mock_module_instance = mock.MagicMock()
            mock_module.ClassName = mock_module_class
            mock_module_class.return_value = mock_module_instance
            mock_module_class.__name__ = module_name
            self.mock_modules[module_name] = (mock_module, mock_module_instance)
            
        def side_effect(name):
            if name in self.mock_modules:
                return self.mock_modules[name][0]
            return mock.MagicMock()
            
        self.mock_import_module.side_effect = side_effect
        
        # Create scanner instance
        with mock.patch('sfscan.SpiderFootDb', return_value=self.dbh):
            self.scanner = SpiderFootScanner(
                self.scanName, 
                self.scanId, 
                self.scanTarget, 
                self.targetType,
                self.moduleList,
                self.config,
                self.loggingQueue
            )
    
    def tearDown(self):
        """Clean up after test case."""
        self.import_module_patcher.stop()
        
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.scanner.scanName, self.scanName)
        self.assertEqual(self.scanner.scanId, self.scanId)
        self.assertEqual(self.scanner.targetValue, self.scanTarget)
        self.assertEqual(self.scanner.targetType, self.targetType)
        self.assertEqual(self.scanner.moduleList, self.moduleList)
        self.assertEqual(self.scanner.config, self.config)
        self.assertEqual(self.scanner.loggingQueue, self.loggingQueue)
        self.assertIsNotNone(self.scanner.sf)
        self.assertIsNotNone(self.scanner.dbh)
        
    def test_load_modules(self):
        """Test loading modules."""
        # Call _loadModules method
        self.scanner._loadModules()
        
        # Verify modules were loaded
        self.assertEqual(len(self.scanner.moduleInstances), 2)
        for module_name in self.moduleList:
            self.assertIn(module_name, self.scanner.moduleInstances)
            
    def test_module_execution_flow(self):
        """Test module execution flow."""
        # Load modules
        self.scanner._loadModules()
        
        # Mock scan instance
        self.dbh.scanInstanceGet.return_value = [
            self.scanName, self.scanTarget, 0, 0, 0, "RUNNING"
        ]
        
        # Mock module inter-dependencies
        for module_name, (_, instance) in self.mock_modules.items():
            instance.watchedEvents.return_value = ["ROOT"]
        
        with mock.patch.object(self.scanner, '_moduleExecute') as mock_execute:
            # Run go method
            self.scanner.go()
            
            # Verify each module was executed once
            self.assertEqual(mock_execute.call_count, len(self.moduleList))
            
    def test_module_execute(self):
        """Test _moduleExecute method."""
        # Load modules
        self.scanner._loadModules()
        
        # Get a test module
        module_name = self.moduleList[0]
        module = self.mock_modules[module_name][1]
        
        # Configure mock module
        module.watchedEvents.return_value = ["ROOT"]
        
        # Create event for module to process
        event_queue = queue.Queue()
        event_queue.put("test_event")
        
        # Call moduleExecute directly
        self.scanner._moduleExecute(module_name, event_queue)
        
        # Verify module's handleEvent was called
        module.handleEvent.assert_called_once_with("test_event")
        
    @mock.patch('time.sleep')
    def test_module_execute_with_error(self, mock_sleep):
        """Test _moduleExecute method with error in module."""
        # Load modules
        self.scanner._loadModules()
        
        # Get a test module
        module_name = self.moduleList[0]
        module = self.mock_modules[module_name][1]
        
        # Configure mock module to raise exception
        module.watchedEvents.return_value = ["ROOT"]
        module.handleEvent.side_effect = Exception("Test error")
        
        # Create event for module to process
        event_queue = queue.Queue()
        event_queue.put("test_event")
        
        # Call moduleExecute directly
        self.scanner._moduleExecute(module_name, event_queue)
        
        # Verify error state was set
        self.assertTrue(module.errorState)
        
    @mock.patch('multiprocessing.Process')
    def test_start_spiderfoot_scanner(self, mock_process):
        """Test startSpiderFootScanner function."""
        # Mock process instance
        mock_process_instance = mock.MagicMock()
        mock_process.return_value = mock_process_instance
        
        # Call startSpiderFootScanner
        loggingQueue = mp.Queue()
        startSpiderFootScanner(
            loggingQueue,
            "Test Scan",
            "test-id",
            "example.com",
            "INTERNET_NAME",
            ["sfp_test1"],
            {}
        )
        
        # Verify process was created and started
        mock_process.assert_called_once()
        mock_process_instance.start.assert_called_once()


class TestSpiderFootScannerIntegration(unittest.TestCase):
    """Integration tests for SpiderFootScanner."""
    
    @mock.patch('sfscan.SpiderFootDb')
    @mock.patch('sflib.SpiderFoot')
    def test_scanner_startup_shutdown(self, mock_sf, mock_db):
        """Test scanner startup and shutdown."""
        # Create mock objects
        mock_sf_instance = mock.MagicMock()
        mock_sf.return_value = mock_sf_instance
        
        mock_db_instance = mock.MagicMock()
        mock_db.return_value = mock_db_instance
        
        # Mock scan status
        mock_db_instance.scanInstanceGet.return_value = [
            "Test Scan", "example.com", 0, 0, 0, "RUNNING"
        ]
        
        # Create temp queues for testing
        loggingQueue = mp.Queue()
        
        # Minimal config
        config = {
            '_debug': False,
            '_maxthreads': 1,
            '__modules__': {}
        }
        
        # Create scanner with empty module list (will exit quickly)
        scanner = SpiderFootScanner(
            "Test Scan",
            "test-id", 
            "example.com",
            "INTERNET_NAME",
            [],
            config,
            loggingQueue
        )
        
        # Run scanner - should exit cleanly
        scanner.go()
        
        # Verify DB calls
        mock_db_instance.scanInstanceSet.assert_called_with(
            "test-id", status="FINISHED"
        )


if __name__ == '__main__':
    unittest.main()
