"""Unit tests for spiderfoot.db module."""

import unittest
import tempfile
import os
import sqlite3
from unittest import mock

from spiderfoot.db import SpiderFootDb
from spiderfoot.event import SpiderFootEvent


class TestSpiderFootDb(unittest.TestCase):
    """Test cases for SpiderFootDb."""

    def setUp(self):
        """Set up test case."""
        # Create a temporary database file
        self.temp_db_file = tempfile.NamedTemporaryFile(
            suffix=".db", delete=False).name
        self.opts = {"__database": self.temp_db_file}
        self.db = SpiderFootDb(self.opts)

        # Set up a test scan
        self.test_scan_id = "test-scan-id"
        self.test_scan_name = "Test Scan"
        self.test_scan_target = "example.com"

        # Create scan instance
        self.db.scanInstanceCreate(
            self.test_scan_id, self.test_scan_name, self.test_scan_target
        )

    def tearDown(self):
        """Clean up after test case."""
        # Close database connection
        self.db.close()

        # Remove temporary database file
        if os.path.exists(self.temp_db_file):
            os.unlink(self.temp_db_file)

    def test_create_schema(self):
        """Test schema creation."""
        # This implicitly tests create_schema which is called during init

        # Check if tables exist
        with sqlite3.connect(self.temp_db_file) as conn:
            cursor = conn.cursor()
            # Check for some key tables
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tbl_scan_instance'"
            )
            self.assertIsNotNone(cursor.fetchone())

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tbl_scan_results'"
            )
            self.assertIsNotNone(cursor.fetchone())

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tbl_event_types'"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_scan_instance_create_and_get(self):
        """Test creating and retrieving a scan instance."""
        scan_id = "test-scan-creation"
        scan_name = "Test Scan Creation"
        scan_target = "example.org"

        # Create scan instance
        self.db.scanInstanceCreate(scan_id, scan_name, scan_target)

        # Get scan instance
        scan_instance = self.db.scanInstanceGet(scan_id)

        # Verify scan instance
        self.assertIsNotNone(scan_instance)
        self.assertEqual(scan_instance[0], scan_name)
        self.assertEqual(scan_instance[1], scan_target)

    def test_scan_instance_set(self):
        """Test updating a scan instance."""
        # Set scan status
        self.db.scanInstanceSet(self.test_scan_id, status="RUNNING")

        # Check if status was updated
        scan_instance = self.db.scanInstanceGet(self.test_scan_id)
        self.assertEqual(scan_instance[5], "RUNNING")

        # Set scan status again
        self.db.scanInstanceSet(self.test_scan_id, status="FINISHED")

        # Check if status was updated
        scan_instance = self.db.scanInstanceGet(self.test_scan_id)
        self.assertEqual(scan_instance[5], "FINISHED")

    def test_scan_instance_list(self):
        """Test listing scan instances."""
        # Create another scan instance
        self.db.scanInstanceCreate(
            "test-scan-id-2", "Test Scan 2", "example.org")

        # Get scan list
        scan_list = self.db.scanInstanceList()

        # Verify scan list
        self.assertEqual(len(scan_list), 2)
        scan_ids = [scan[0] for scan in scan_list]
        self.assertIn(self.test_scan_id, scan_ids)
        self.assertIn("test-scan-id-2", scan_ids)

    def test_scan_instance_delete(self):
        """Test deleting a scan instance."""
        # Create a scan to delete
        delete_scan_id = "scan-to-delete"
        self.db.scanInstanceCreate(
            delete_scan_id, "Scan to Delete", "example.org")

        # Verify it exists
        self.assertIsNotNone(self.db.scanInstanceGet(delete_scan_id))

        # Delete the scan
        result = self.db.scanInstanceDelete(delete_scan_id)
        self.assertTrue(result)

        # Verify it's gone
        self.assertIsNone(self.db.scanInstanceGet(delete_scan_id))

    def test_scan_log_event(self):
        """Test logging events to a scan."""
        # Log an event
        self.db.scanLogEvent(self.test_scan_id, "TEST",
                             "Test message", "TestModule")

        # Get logs
        logs = self.db.scanLogs(self.test_scan_id)

        # Verify logs
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0][1], "TestModule")
        self.assertEqual(logs[0][2], "TEST")
        self.assertEqual(logs[0][3], "Test message")

    def test_scan_log_events_batch(self):
        """Test logging events in batch."""
        # Create batch of events
        batch = [
            (self.test_scan_id, "TEST", "Test message 1", "TestModule", 0),
            (self.test_scan_id, "TEST", "Test message 2", "TestModule", 0),
        ]

        # Log events in batch
        result = self.db.scanLogEvents(batch)
        self.assertTrue(result)

        # Get logs
        logs = self.db.scanLogs(self.test_scan_id)

        # Verify logs
        self.assertEqual(len(logs), 2)

    def test_event_types(self):
        """Test getting event types."""
        # Get event types
        event_types = self.db.eventTypes()

        # Verify event types exist (should be seeded during schema creation)
        self.assertGreater(len(event_types), 0)

        # Check for some common event types
        event_type_names = [et[1] for et in event_types]
        self.assertIn("INTERNET_NAME", event_type_names)
        self.assertIn("IP_ADDRESS", event_type_names)
        self.assertIn("DOMAIN_NAME", event_type_names)

    def test_scan_event_store_and_retrieve(self):
        """Test storing and retrieving scan events."""
        # Create a test event
        source_event = SpiderFootEvent(
            "ROOT", self.test_scan_target, "TEST", "")
        evt = SpiderFootEvent(
            "INTERNET_NAME", "example.com", "test_module", source_event
        )

        # Store the event
        self.db.scanEventStore(self.test_scan_id, evt)

        # Retrieve events
        events = self.db.scanResultEvent(self.test_scan_id)

        # Verify events
        self.assertEqual(len(events), 1)
        retrieved_event = events[0]
        self.assertEqual(retrieved_event[1], "example.com")  # data
        self.assertEqual(retrieved_event[4], "INTERNET_NAME")  # type
        self.assertEqual(retrieved_event[7], "test_module")  # module

    def test_config_set_and_get(self):
        """Test setting and getting configuration."""
        # Set config
        test_config = {"test_opt1": "test_val1", "test_opt2": "test_val2"}
        result = self.db.configSet(test_config)
        self.assertTrue(result)

        # Get config
        config = self.db.configGet()

        # Verify config
        self.assertIn("test_opt1", config)
        self.assertEqual(config["test_opt1"], "test_val1")
        self.assertIn("test_opt2", config)
        self.assertEqual(config["test_opt2"], "test_val2")

    def test_scan_config_set_and_get(self):
        """Test setting and getting scan configuration."""
        # Set scan config
        test_config = {"test_opt1": "test_val1", "test_opt2": "test_val2"}
        self.db.scanConfigSet(self.test_scan_id, test_config)

        # Get scan config
        config = self.db.scanConfigGet(self.test_scan_id)

        # Verify config
        self.assertIn("test_opt1", config)
        self.assertEqual(config["test_opt1"], "test_val1")
        self.assertIn("test_opt2", config)
        self.assertEqual(config["test_opt2"], "test_val2")

    def test_search(self):
        """Test search functionality."""
        # Create a test event
        source_event = SpiderFootEvent(
            "ROOT", self.test_scan_target, "TEST", "")
        evt = SpiderFootEvent(
            "INTERNET_NAME", "example.com", "test_module", source_event
        )

        # Store the event
        self.db.scanEventStore(self.test_scan_id, evt)

        # Search for the event
        criteria = {
            "scan_id": self.test_scan_id,
            "type": "INTERNET_NAME",
            "value": "example.com",
        }
        results = self.db.search(criteria)

        # Verify results
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result[1], "example.com")
        self.assertEqual(result[4], "INTERNET_NAME")

    @mock.patch("sqlite3.connect")
    def test_database_connection_error(self, mock_connect):
        """Test database connection error handling."""
        # Mock connection error
        mock_connect.side_effect = sqlite3.Error("Mock connection error")

        # Attempt to create database
        with self.assertRaises(IOError):
            SpiderFootDb({"__database": "non-existent.db"})

    def test_vacuum_db(self):
        """Test database vacuum function."""
        # Should succeed with SQLite
        result = self.db.vacuumDB()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
