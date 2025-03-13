"""Unit tests for spiderfoot.target module."""

import unittest
from unittest import mock
from spiderfoot.target import SpiderFootTarget


class TestSpiderFootTarget(unittest.TestCase):
    """Test cases for SpiderFootTarget."""

    def test_init_with_valid_parameters(self):
        """Test initializing target with valid parameters."""
        target = SpiderFootTarget("example.com", "INTERNET_NAME")

        # Check attributes
        self.assertEqual(target.targetType, "INTERNET_NAME")
        self.assertEqual(target.targetValue, "example.com")
        self.assertEqual(target.targetAliases, [])

    def test_init_with_invalid_target_type(self):
        """Test initializing target with invalid target type."""
        with self.assertRaises(TypeError):
            SpiderFootTarget("example.com", None)

        with self.assertRaises(ValueError):
            SpiderFootTarget("example.com", "")

        with self.assertRaises(ValueError):
            SpiderFootTarget("example.com", "INVALID_TYPE")

    def test_init_with_invalid_target_value(self):
        """Test initializing target with invalid target value."""
        with self.assertRaises(TypeError):
            SpiderFootTarget(None, "INTERNET_NAME")

        with self.assertRaises(ValueError):
            SpiderFootTarget("", "INTERNET_NAME")

    def test_set_alias(self):
        """Test setting target alias."""
        target = SpiderFootTarget("example.com", "INTERNET_NAME")

        # Set aliases
        target.setAlias("alias.example.com", "INTERNET_NAME")
        target.setAlias("192.168.0.1", "IP_ADDRESS")

        # Check aliases
        self.assertEqual(len(target.targetAliases), 2)
        # Check alias values
        alias_values = [alias["value"] for alias in target.targetAliases]
        self.assertIn("alias.example.com", alias_values)
        self.assertIn("192.168.0.1", alias_values)
        # Check alias types
        alias_types = [alias["type"] for alias in target.targetAliases]
        self.assertIn("INTERNET_NAME", alias_types)
        self.assertIn("IP_ADDRESS", alias_types)

    def test_set_invalid_alias(self):
        """Test setting invalid target alias."""
        target = SpiderFootTarget("example.com", "INTERNET_NAME")

        # Set invalid aliases
        target.setAlias(None, "INTERNET_NAME")
        target.setAlias("", "INTERNET_NAME")
        target.setAlias("valid", None)
        target.setAlias("valid", "")

        # Check that no aliases were added
        self.assertEqual(len(target.targetAliases), 0)

    def test_set_duplicate_alias(self):
        """Test setting duplicate target alias."""
        target = SpiderFootTarget("example.com", "INTERNET_NAME")

        # Set alias
        target.setAlias("alias.example.com", "INTERNET_NAME")
        # Set duplicate alias
        target.setAlias("alias.example.com", "INTERNET_NAME")

        # Check that only one alias was added
        self.assertEqual(len(target.targetAliases), 1)

    def test_get_equivalents(self):
        """Test getting target equivalents."""
        # Test for INTERNET_NAME
        target = SpiderFootTarget("example.com", "INTERNET_NAME")
        equivalents = target._getEquivalents("INTERNET_NAME")
        self.assertEqual(equivalents, [])

        # Add an alias and test again
        target.setAlias("alias.example.com", "INTERNET_NAME")
        equivalents = target._getEquivalents("INTERNET_NAME")
        self.assertEqual(equivalents, ["alias.example.com"])

        # Test for IP_ADDRESS
        target = SpiderFootTarget("192.168.0.1", "IP_ADDRESS")
        equivalents = target._getEquivalents("IP_ADDRESS")
        self.assertEqual(equivalents, [])

        # Add an alias and test again
        target.setAlias("192.168.0.2", "IP_ADDRESS")
        equivalents = target._getEquivalents("IP_ADDRESS")
        self.assertEqual(equivalents, ["192.168.0.2"])

    def test_get_names(self):
        """Test getting domain names."""
        target = SpiderFootTarget("example.com", "INTERNET_NAME")

        # Initially should only contain the target value
        names = target.getNames()
        self.assertEqual(names, ["example.com"])

        # Add aliases and test again
        target.setAlias("alias.example.com", "INTERNET_NAME")
        target.setAlias("another.example.com", "INTERNET_NAME")
        names = target.getNames()
        self.assertEqual(len(names), 3)
        self.assertIn("example.com", names)
        self.assertIn("alias.example.com", names)
        self.assertIn("another.example.com", names)

        # Test with email target
        email_target = SpiderFootTarget("user@example.org", "EMAILADDR")
        email_target.setAlias("example.org", "INTERNET_NAME")
        names = email_target.getNames()
        self.assertEqual(len(names), 1)
        self.assertIn("example.org", names)

    def test_get_addresses(self):
        """Test getting IP addresses."""
        target = SpiderFootTarget("192.168.0.1", "IP_ADDRESS")

        # Initially should only contain the target value
        addresses = target.getAddresses()
        self.assertEqual(addresses, ["192.168.0.1"])

        # Add aliases and test again
        target.setAlias("192.168.0.2", "IP_ADDRESS")
        target.setAlias("2001:db8::1", "IPV6_ADDRESS")
        addresses = target.getAddresses()
        self.assertEqual(len(addresses), 2)  # IPv4 only
        self.assertIn("192.168.0.1", addresses)
        self.assertIn("192.168.0.2", addresses)

        # Test IPv6 address
        ipv6_target = SpiderFootTarget("2001:db8::2", "IPV6_ADDRESS")
        addresses = ipv6_target.getAddresses()
        self.assertEqual(addresses, ["2001:db8::2"])

    @mock.patch("netaddr.IPAddress")
    @mock.patch("netaddr.IPNetwork")
    def test_matches(self, mock_ipnetwork, mock_ipaddress):
        """Test target matching."""
        # Test matching for regular targets
        target = SpiderFootTarget("example.com", "INTERNET_NAME")
        target.setAlias("alias.example.com", "INTERNET_NAME")

        # Test exact match
        self.assertTrue(target.matches("example.com"))
        self.assertTrue(target.matches("alias.example.com"))

        # Test parent/child domain matching
        self.assertTrue(
            target.matches(
                "sub.example.com", includeParents=False, includeChildren=True
            )
        )
        self.assertTrue(
            target.matches("com", includeParents=True, includeChildren=False)
        )
        self.assertFalse(
            target.matches(
                "sub.example.com", includeParents=False, includeChildren=False
            )
        )
        self.assertFalse(
            target.matches("com", includeParents=False, includeChildren=False)
        )

        # Test non-matching
        self.assertFalse(target.matches("different.com"))

        # Test with IP addresses
        ip_target = SpiderFootTarget("192.168.0.1", "IP_ADDRESS")

        # Mock netaddr functions for IP matching tests
        mock_ipaddress.return_value = "192.168.0.1"
        mock_ipnetwork.return_value = ["192.168.0.1", "192.168.0.2"]

        # Test exact match
        self.assertTrue(ip_target.matches("192.168.0.1"))

        # Test IP in subnet match
        self.assertTrue(ip_target.matches("192.168.0.2"))

        # Test non-matching IP
        mock_ipaddress.return_value = "10.0.0.1"
        mock_ipnetwork.return_value = ["10.0.0.1"]
        self.assertFalse(ip_target.matches("10.0.0.1"))

        # Test with human name and other special targets
        human_target = SpiderFootTarget("John Doe", "HUMAN_NAME")
        self.assertTrue(
            human_target.matches("anything")
        )  # All matches return True for special targets

        username_target = SpiderFootTarget("johndoe", "USERNAME")
        self.assertTrue(
            username_target.matches("anything")
        )  # All matches return True for special targets

        bitcoin_target = SpiderFootTarget(
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "BITCOIN_ADDRESS"
        )
        self.assertTrue(
            bitcoin_target.matches("anything")
        )  # All matches return True for special targets

        phone_target = SpiderFootTarget("+12125551212", "PHONE_NUMBER")
        self.assertTrue(
            phone_target.matches("anything")
        )  # All matches return True for special targets

    def test_matches_invalid_value(self):
        """Test matching with invalid value."""
        target = SpiderFootTarget("example.com", "INTERNET_NAME")

        # Test with None
        self.assertFalse(target.matches(None))

        # Test with empty string
        self.assertFalse(target.matches(""))

        # Test with non-string
        self.assertFalse(target.matches(123))


if __name__ == "__main__":
    unittest.main()
