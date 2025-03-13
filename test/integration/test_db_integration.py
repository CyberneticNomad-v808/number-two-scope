"""Integration tests for SpiderFootDb."""

import os
import unittest
import tempfile

from spiderfoot.db import SpiderFootDb
from spiderfoot.event import SpiderFootEvent


class TestSpiderFootDbIntegration(unittest.TestCase):
    """Integration tests for SpiderFootDb."""

    def setUp(self):
        """Set up test case."""
        # Create a temporary database file
        self.temp_db_file = tempfile.NamedTemporaryFile(
            suffix=".db", delete=False).name
        self.opts = {"__database": self.temp_db_file}
        self.db = SpiderFootDb(self.opts)

    def tearDown(self):
        """Clean up after test case."""
        # Close database connection
        self.db.close()

        # Remove temporary database file
        if os.path.exists(self.temp_db_file):
            os.unlink(self.temp_db_file)

    def test_full_scan_workflow(self):
        """Test a full scan workflow with database operations."""
        # 1. Create a scan
        scan_id = "test-scan-workflow"
        scan_name = "Test Scan Workflow"
        scan_target = "example.com"

        self.db.scanInstanceCreate(scan_id, scan_name, scan_target)

        # 2. Update scan status to RUNNING
        self.db.scanInstanceSet(scan_id, status="RUNNING", started=1234567890)
        scan_info = self.db.scanInstanceGet(scan_id)
        self.assertEqual(scan_info[5], "RUNNING")

        # 3. Store some configuration
        scan_config = {
            "module1.enabled": "1",
            "module2.enabled": "1",
            "module1.option": "test value",
        }
        self.db.scanConfigSet(scan_id, scan_config)

        # 4. Store some logs
        self.db.scanLogEvent(scan_id, "INFO", "Starting scan", "test_module")
        self.db.scanLogEvent(scan_id, "DEBUG", "Debug message", "test_module")

        # 5. Store some events
        root_event = SpiderFootEvent("ROOT", scan_target, "test_module")
        self.db.scanEventStore(scan_id, root_event)

        child_event = SpiderFootEvent(
            "DOMAIN_NAME", "subdomain.example.com", "test_module", root_event
        )
        self.db.scanEventStore(scan_id, child_event)

        ip_event = SpiderFootEvent(
            "IP_ADDRESS", "192.168.1.1", "test_module", child_event
        )
        self.db.scanEventStore(scan_id, ip_event)

        # 6. Mark scan as finished
        self.db.scanInstanceSet(scan_id, status="FINISHED", ended=1234569890)

        # 7. Verify scan status
        scan_info = self.db.scanInstanceGet(scan_id)
        self.assertEqual(scan_info[5], "FINISHED")

        # 8. Verify scan logs
        logs = self.db.scanLogs(scan_id)
        self.assertEqual(len(logs), 2)

        # 9. Verify scan events
        events = self.db.scanResultEvent(scan_id)
        self.assertEqual(len(events), 3)

        # 10. Verify event relationships
        # Find the IP_ADDRESS event
        ip_events = self.db.scanResultEvent(scan_id, eventType="IP_ADDRESS")
        self.assertEqual(len(ip_events), 1)
        ip_event_data = ip_events[0]

        # Get the source event for the IP address
        src_event_hash = ip_event_data[9]  # source_event_hash column
        src_events = self.db.scanResultEventUnique(
            scan_id, eventHash=src_event_hash)
        self.assertEqual(len(src_events), 1)
        src_event_data = src_events[0]
        self.assertEqual(src_event_data[4], "DOMAIN_NAME")  # type column

        # 11. Verify scan summary
        summary = self.db.scanResultSummary(scan_id)
        summary_dict = {item[0]: item[1] for item in summary}
        self.assertEqual(summary_dict["DOMAIN_NAME"], 1)
        self.assertEqual(summary_dict["IP_ADDRESS"], 1)
        self.assertEqual(summary_dict["ROOT"], 1)

        # 12. Search for specific data
        search_results = self.db.search(
            {"scan_id": scan_id, "type": "IP_ADDRESS", "value": "192.168.1.1"}
        )
        self.assertEqual(len(search_results), 1)

        # 13. Delete scan and verify it's gone
        self.db.scanInstanceDelete(scan_id)
        self.assertIsNone(self.db.scanInstanceGet(scan_id))
        self.assertEqual(len(self.db.scanResultEvent(scan_id)), 0)


if __name__ == "__main__":
    unittest.main()
