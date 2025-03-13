"""Unit tests for spiderfoot.correlation module."""

import unittest
from unittest import mock
import yaml
import uuid

from spiderfoot.correlation import SpiderFootCorrelator
from spiderfoot.db import SpiderFootDb


class TestSpiderFootCorrelator(unittest.TestCase):
    """Test cases for SpiderFootCorrelator class."""

    def setUp(self):
        """Set up test case."""
        # Mock SpiderFootDb
        self.mock_db = mock.MagicMock(spec=SpiderFootDb)

        # Sample correlation rule
        self.test_rule = """
        id: test_rule_id
        name: Test Correlation Rule
        description: A rule for testing
        risk: INFO
        collections:
          - id: domains
            types: 
              - DOMAIN_NAME
              - INTERNET_NAME
          - id: emails
            types:
              - EMAILADDR
        logic:
          - conditions:
              - from: domains
                field: data
                method: regex
                value: "example\\.com$"
            title: Found example.com domain
        """

        # Sample rule list
        self.rule_list = [self.test_rule]

        # Create correlator
        self.correlator = SpiderFootCorrelator(
            self.mock_db, self.rule_list, "SCAN123")

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.correlator.dbh, self.mock_db)
        self.assertEqual(self.correlator.scanId, "SCAN123")
        self.assertEqual(len(self.correlator.rules), 1)

        # Verify rule was parsed correctly
        rule = self.correlator.rules[0]
        self.assertEqual(rule["id"], "test_rule_id")
        self.assertEqual(rule["name"], "Test Correlation Rule")
        self.assertEqual(rule["description"], "A rule for testing")
        self.assertEqual(rule["risk"], "INFO")

    def test_init_with_invalid_parameters(self):
        """Test initialization with invalid parameters."""
        # Test with non-SpiderFootDb
        with self.assertRaises(TypeError):
            SpiderFootCorrelator("not_a_db", self.rule_list, "SCAN123")

        # Test with non-list rules
        with self.assertRaises(TypeError):
            SpiderFootCorrelator(self.mock_db, "not_a_list", "SCAN123")

        # Test with non-string scanId
        with self.assertRaises(TypeError):
            SpiderFootCorrelator(self.mock_db, self.rule_list, 123)

        # Test with empty scanId
        with self.assertRaises(ValueError):
            SpiderFootCorrelator(self.mock_db, self.rule_list, "")

    def test_load_event_data(self):
        """Test _load_event_data method."""
        # Mock database response
        self.mock_db.scanResultEvent.return_value = [
            # Format: [id, data, source_data, module, type, ...]
            [
                1,
                "example.com",
                "source data",
                "module",
                "DOMAIN_NAME",
                None,
                None,
                None,
                "hash1",
                "source_hash1",
            ],
            [
                2,
                "test.example.com",
                "source data",
                "module",
                "INTERNET_NAME",
                None,
                None,
                None,
                "hash2",
                "source_hash2",
            ],
        ]

        # Call method
        result = self.correlator._load_event_data(self.correlator.rules[0])

        # Verify result
        self.assertIn("domains", result)
        self.assertEqual(len(result["domains"]), 2)

        # Verify database was called correctly
        calls = [
            mock.call("SCAN123", eventType="DOMAIN_NAME", filterFp=True),
            mock.call("SCAN123", eventType="INTERNET_NAME", filterFp=True),
        ]
        self.mock_db.scanResultEvent.assert_has_calls(calls, any_order=True)

    def test_run_rule_evaluation(self):
        """Test _run_rule_evaluation method."""
        # Create test data
        event_data = {
            "domains": [
                {
                    "type": "DOMAIN_NAME",
                    "data": "example.com",
                    "module": "test_module",
                    "source_data": "test data",
                    "hash": "hash1",
                    "source_event_hash": "source_hash1",
                }
            ]
        }

        # Call method
        results = self.correlator._run_rule_evaluation(
            self.correlator.rules[0], event_data
        )

        # Verify results
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result["title"], "Found example.com domain")
        self.assertEqual(result["rule_id"], "test_rule_id")
        self.assertEqual(result["rule_name"], "Test Correlation Rule")
        self.assertEqual(result["rule_risk"], "INFO")
        self.assertIn("hash1", result["events"])

    def test_run_correlations(self):
        """Test run_correlations method."""
        # Mock database responses
        self.mock_db.scanResultEvent.return_value = [
            # Format: [id, data, source_data, module, type, ...]
            [
                1,
                "example.com",
                "source data",
                "module",
                "DOMAIN_NAME",
                None,
                None,
                None,
                "hash1",
                "source_hash1",
            ]
        ]

        # Patch _run_rule_evaluation to return a known result
        with mock.patch.object(self.correlator, "_run_rule_evaluation") as mock_eval:
            mock_eval.return_value = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Test correlation",
                    "rule_id": "test_rule_id",
                    "rule_name": "Test Rule",
                    "rule_descr": "Test description",
                    "rule_risk": "INFO",
                    "rule_logic": "test logic",
                    "events": ["hash1"],
                }
            ]

            # Run correlations
            results = self.correlator.run_correlations()

            # Verify results
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "Test correlation")

            # Verify database was called to store correlation
            self.mock_db.correlationResultCreate.assert_called_once()

    def test_run_correlations_with_error(self):
        """Test run_correlations method with error."""
        # Mock database to raise an exception
        self.mock_db.scanResultEvent.side_effect = Exception(
            "Test database error")

        # Run correlations (should not raise exception)
        results = self.correlator.run_correlations()

        # Should return empty results
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
