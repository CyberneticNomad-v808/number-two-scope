"""Unit tests for spiderfoot.plugin module."""

import unittest
from unittest import mock
import logging

from spiderfoot.plugin import SpiderFootPlugin
from spiderfoot.event import SpiderFootEvent


class TestSpiderFootPlugin(unittest.TestCase):
    """Test cases for SpiderFootPlugin class."""

    def setUp(self):
        """Set up test case."""
        self.module_name = "sfp_test"
        self.opts = {'_debug': True}
        self.plugin = SpiderFootPlugin()
        self.plugin.__name__ = self.module_name
        self.plugin.opts = self.opts.copy()
        
        # Create a test event
        self.event = SpiderFootEvent("TEST", "test data", "test_module")

    def test_init(self):
        """Test initialization."""
        plugin = SpiderFootPlugin()
        self.assertIsNone(plugin.sf)
        self.assertFalse(plugin.errorState)
        self.assertIsNone(plugin._currentEvent)
        
    def test_debug(self):
        """Test debug method."""
        with mock.patch.object(self.plugin, '_log') as mock_log:
            self.plugin.debug("Test debug message")
            mock_log.assert_called_once_with(logging.DEBUG, "Test debug message")

    def test_info(self):
        """Test info method."""
        with mock.patch.object(self.plugin, '_log') as mock_log:
            self.plugin.info("Test info message")
            mock_log.assert_called_once_with(logging.INFO, "Test info message")

    def test_error(self):
        """Test error method."""
        with mock.patch.object(self.plugin, '_log') as mock_log:
            self.plugin.error("Test error message")
            mock_log.assert_called_once_with(logging.ERROR, "Test error message")

    def test_set_target(self):
        """Test setTarget method."""
        # Mock SpiderFootTarget
        target = mock.MagicMock()
        
        # Call setTarget
        self.plugin.setTarget(target)
        
        # Verify target was set
        self.assertEqual(self.plugin._currentTarget, target)
        
        # Test with invalid target
        with self.assertRaises(TypeError):
            self.plugin.setTarget("not a target")

    def test_register_listener(self):
        """Test registerListener method."""
        # Create mock listener
        listener = mock.MagicMock()
        
        # Register listener
        self.plugin.registerListener(listener)
        
        # Verify listener was added
        self.assertIn(listener, self.plugin._listenerModules)

    def test_set_db_h(self):
        """Test setDbh method."""
        # Create mock db handle
        dbh = mock.MagicMock()
        
        # Set db handle
        self.plugin.setDbh(dbh)
        
        # Verify db handle was set
        self.assertEqual(self.plugin.__sfdb__, dbh)

    def test_set_scan_id(self):
        """Test setScanId method."""
        # Set scan ID
        self.plugin.setScanId("SCAN123")
        
        # Verify scan ID was set
        self.assertEqual(self.plugin.__scanId__, "SCAN123")
        
        # Test with invalid scan ID
        with self.assertRaises(TypeError):
            self.plugin.setScanId(None)

    def test_get_scan_id(self):
        """Test getScanId method."""
        # Set scan ID
        self.plugin.__scanId__ = "SCAN123"
        
        # Get scan ID
        scan_id = self.plugin.getScanId()
        
        # Verify scan ID
        self.assertEqual(scan_id, "SCAN123")
        
        # Test with no scan ID
        self.plugin.__scanId__ = None
        with self.assertRaises(TypeError):
            self.plugin.getScanId()

    def test_default_watched_events(self):
        """Test default watchedEvents method."""
        # Default watchedEvents should return ["*"]
        self.assertEqual(self.plugin.watchedEvents(), ["*"])

    def test_default_produced_events(self):
        """Test default producedEvents method."""
        # Default producedEvents should return empty list
        self.assertEqual(self.plugin.producedEvents(), [])

    def test_check_for_stop(self):
        """Test checkForStop method."""
        # Test when errorState is True
        self.plugin.errorState = True
        self.assertTrue(self.plugin.checkForStop())
        
        # Test when _stopScanning is True
        self.plugin.errorState = False
        self.plugin._stopScanning = True
        self.assertTrue(self.plugin.checkForStop())
        
        # Test when scanId is set but db returns None
        self.plugin._stopScanning = False
        self.plugin.__scanId__ = "SCAN123"
        self.plugin.__sfdb__ = mock.MagicMock(scanInstanceGet=mock.MagicMock(return_value=None))
        self.assertFalse(self.plugin.checkForStop())
        
        # Test when scan status is ABORT-REQUESTED
        mock_scan = ("Name", "Target", 1, 1, 1, "ABORT-REQUESTED")
        self.plugin.__sfdb__.scanInstanceGet.return_value = mock_scan
        self.assertTrue(self.plugin.checkForStop())
        self.assertTrue(self.plugin._stopScanning)
        
        # Test when scan status is RUNNING
        mock_scan = ("Name", "Target", 1, 1, 1, "RUNNING")
        self.plugin._stopScanning = False
        self.plugin.__sfdb__.scanInstanceGet.return_value = mock_scan
        self.assertFalse(self.plugin.checkForStop())
        self.assertFalse(self.plugin._stopScanning)

    @mock.patch('spiderfoot.plugin.SpiderFootEvent')
    def test_notify_listeners(self, mock_event):
        """Test notifyListeners method."""
        # Create mock listeners
        listener1 = mock.MagicMock(watchedEvents=mock.MagicMock(return_value=["TEST"]))
        listener2 = mock.MagicMock(watchedEvents=mock.MagicMock(return_value=["OTHER"]))
        self.plugin._listenerModules = [listener1, listener2]
        
        # Create event
        event = mock.MagicMock(eventType="TEST", data="test data")
        mock_event.return_value = event
        
        # Notify listeners
        self.plugin.notifyListeners(event)
        
        # Verify listener1 was called but listener2 was not
        listener1.handleEvent.assert_called_once_with(event)
        listener2.handleEvent.assert_not_called()
        
        # Test with output filter
        self.plugin.__outputFilter__ = "TEST"
        event.eventType = "OTHER"
        self.plugin.notifyListeners(event)
        # Listener1 shouldn't be called
        self.assertEqual(listener1.handleEvent.call_count, 1)
        
    def test_as_dict(self):
        """Test asdict method."""
        # Set up plugin attributes
        self.plugin.meta = {
            "name": "Test Plugin",
            "summary": "Test Summary",
            "flags": ["flag1", "flag2"],
            "useCases": ["use case 1"],
            "categories": ["category 1"]
        }
        self.plugin.opts = {"option1": "value1"}
        self.plugin.optdescs = {"option1": "Option 1 description"}
        
        # Mock methods
        self.plugin.producedEvents = mock.MagicMock(return_value=["EVENT1"])
        self.plugin.watchedEvents = mock.MagicMock(return_value=["EVENT2"])
        
        # Get dictionary representation
        result = self.plugin.asdict()
        
        # Verify result
        self.assertEqual(result["name"], "Test Plugin")
        self.assertEqual(result["descr"], "Test Summary")
        self.assertEqual(result["cats"], ["category 1"])
        self.assertEqual(result["group"], ["use case 1"])
        self.assertEqual(result["labels"], ["flag1", "flag2"])
        self.assertEqual(result["provides"], ["EVENT1"])
        self.assertEqual(result["consumes"], ["EVENT2"])
        self.assertEqual(result["opts"], {"option1": "value1"})
        self.assertEqual(result["optdescs"], {"option1": "Option 1 description"})


if __name__ == "__main__":
    unittest.main()
