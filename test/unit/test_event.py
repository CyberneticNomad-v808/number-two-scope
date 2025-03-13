"""Unit tests for spiderfoot.event module."""

import unittest
import time
from spiderfoot.event import SpiderFootEvent


class TestSpiderFootEvent(unittest.TestCase):
    """Test cases for SpiderFootEvent."""

    def test_init_event_with_valid_parameters(self):
        """Test initializing event with valid parameters."""
        event = SpiderFootEvent("TEST", "test data", "test_module")

        # Check attributes
        self.assertEqual(event.eventType, "TEST")
        self.assertEqual(event.data, "test data")
        self.assertEqual(event.module, "test_module")
        self.assertEqual(event.confidence, 100)  # default
        self.assertEqual(event.visibility, 100)  # default
        self.assertEqual(event.risk, 0)  # default
        # default without source event
        self.assertEqual(event.sourceEventHash, "ROOT")
        self.assertEqual(event.actualSource, "test_module")
        self.assertIsNotNone(event.hash)
        self.assertIsNotNone(event.generated)
        self.assertIsNone(event.sourceEvent)

    def test_init_with_source_event(self):
        """Test initializing event with a source event."""
        source_event = SpiderFootEvent(
            "SOURCE", "source data", "source_module")
        event = SpiderFootEvent("TEST", "test data",
                                "test_module", source_event)

        # Check source event attributes
        self.assertEqual(event.sourceEventHash, source_event.hash)
        self.assertEqual(event.actualSource, "source_module")
        self.assertEqual(event.sourceEvent, source_event)

    def test_init_with_custom_parameters(self):
        """Test initializing event with custom confidence, visibility, and
        risk."""
        event = SpiderFootEvent(
            "TEST", "test data", "test_module", confidence=50, visibility=75, risk=25
        )

        # Check custom parameters
        self.assertEqual(event.confidence, 50)
        self.assertEqual(event.visibility, 75)
        self.assertEqual(event.risk, 25)

    def test_init_with_invalid_event_type(self):
        """Test initializing event with invalid event type."""
        with self.assertRaises(TypeError):
            SpiderFootEvent(None, "test data", "test_module")

        with self.assertRaises(ValueError):
            SpiderFootEvent("", "test data", "test_module")

    def test_init_with_invalid_data(self):
        """Test initializing event with invalid data."""
        with self.assertRaises(TypeError):
            SpiderFootEvent("TEST", None, "test_module")

        with self.assertRaises(ValueError):
            SpiderFootEvent("TEST", "", "test_module")

    def test_init_with_invalid_module(self):
        """Test initializing event with invalid module."""
        with self.assertRaises(TypeError):
            SpiderFootEvent("TEST", "test data", None)

        with self.assertRaises(ValueError):
            SpiderFootEvent("TEST", "test data", "")

    def test_init_with_invalid_confidence(self):
        """Test initializing event with invalid confidence."""
        with self.assertRaises(TypeError):
            SpiderFootEvent("TEST", "test data", "test_module",
                            confidence="invalid")

        with self.assertRaises(ValueError):
            SpiderFootEvent("TEST", "test data", "test_module", confidence=101)

        with self.assertRaises(ValueError):
            SpiderFootEvent("TEST", "test data", "test_module", confidence=-1)

    def test_init_with_invalid_visibility(self):
        """Test initializing event with invalid visibility."""
        with self.assertRaises(TypeError):
            SpiderFootEvent("TEST", "test data", "test_module",
                            visibility="invalid")

        with self.assertRaises(ValueError):
            SpiderFootEvent("TEST", "test data", "test_module", visibility=101)

        with self.assertRaises(ValueError):
            SpiderFootEvent("TEST", "test data", "test_module", visibility=-1)

    def test_init_with_invalid_risk(self):
        """Test initializing event with invalid risk."""
        with self.assertRaises(TypeError):
            SpiderFootEvent("TEST", "test data", "test_module", risk="invalid")

        with self.assertRaises(ValueError):
            SpiderFootEvent("TEST", "test data", "test_module", risk=101)

        with self.assertRaises(ValueError):
            SpiderFootEvent("TEST", "test data", "test_module", risk=-1)

    def test_init_with_invalid_source_event(self):
        """Test initializing event with invalid source event."""
        with self.assertRaises(TypeError):
            SpiderFootEvent("TEST", "test data", "test_module",
                            sourceEvent="invalid")

    def test_generate_hash(self):
        """Test hash generation."""
        event = SpiderFootEvent("TEST", "test data", "test_module")
        event_hash = event.hash

        # Create an identical event - should have the same hash
        identical_event = SpiderFootEvent("TEST", "test data", "test_module")
        self.assertEqual(event_hash, identical_event.hash)

        # Create a different event - should have a different hash
        different_event = SpiderFootEvent(
            "TEST", "different data", "test_module")
        self.assertNotEqual(event_hash, different_event.hash)

    def test_as_dict(self):
        """Test converting event to dictionary."""
        event = SpiderFootEvent("TEST", "test data", "test_module")
        event_dict = event.asDict()

        # Check dictionary keys
        expected_keys = [
            "type",
            "data",
            "module",
            "confidence",
            "visibility",
            "risk",
            "hash",
            "sourceEventHash",
            "actualSource",
            "generated",
        ]
        for key in expected_keys:
            self.assertIn(key, event_dict)

        # Check some values
        self.assertEqual(event_dict["type"], "TEST")
        self.assertEqual(event_dict["data"], "test data")
        self.assertEqual(event_dict["module"], "test_module")
        self.assertEqual(event_dict["hash"], event.hash)

    def test_str_representation(self):
        """Test string representation of event."""
        event = SpiderFootEvent("TEST", "test data", "test_module")
        str_rep = str(event)

        # Check that string representation contains key information
        self.assertIn("TEST", str_rep)
        self.assertIn("test data", str_rep)
        self.assertIn("test_module", str_rep)

    def test_equality(self):
        """Test event equality comparison."""
        event1 = SpiderFootEvent("TEST", "test data", "test_module")
        # Create an identical event
        event2 = SpiderFootEvent("TEST", "test data", "test_module")
        # Create a different event
        event3 = SpiderFootEvent("TEST", "different data", "test_module")

        # Test equality
        self.assertEqual(event1, event2)
        self.assertNotEqual(event1, event3)

        # Test with non-event
        self.assertNotEqual(event1, "not an event")

    def test_hash_function(self):
        """Test that events can be used in sets and dictionaries."""
        event1 = SpiderFootEvent("TEST", "test data", "test_module")
        event2 = SpiderFootEvent("TEST", "test data", "test_module")
        event3 = SpiderFootEvent("TEST", "different data", "test_module")

        # Test in set
        event_set = {event1, event2, event3}
        # Since event1 and event2 are equal, set should have only 2 elements
        self.assertEqual(len(event_set), 2)

        # Test as dictionary key
        event_dict = {event1: "value1", event3: "value3"}
        self.assertEqual(len(event_dict), 2)
        self.assertEqual(event_dict[event1], "value1")
        self.assertEqual(event_dict[event2], "value1")  # event2 equals event1


if __name__ == "__main__":
    unittest.main()
