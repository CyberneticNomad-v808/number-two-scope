"""Tests for SpiderFoot version information."""

import unittest
import re

from spiderfoot import __version__


class TestVersion(unittest.TestCase):
    """Test cases for SpiderFoot version."""

    def test_version_format(self):
        """Test version string follows semantic versioning."""
        # Version should match format like 4.0.0 or 4.0.0-alpha.1
        pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"
        self.assertTrue(
            re.match(pattern, __version__),
            f"Version {__version__} does not match semantic versioning",
        )

    def test_version_components(self):
        """Test version components can be extracted."""
        # Extract major.minor.patch
        base_version = __version__.split("-")[0]
        components = base_version.split(".")

        self.assertEqual(
            len(components), 3, "Version should have major, minor, and patch components"
        )

        # All components should be integers
        for component in components:
            self.assertTrue(
                component.isdigit(
                ), f"Version component {component} is not a number"
            )

        # Extract prerelease if present
        if "-" in __version__:
            prerelease = __version__.split("-")[1]
            self.assertTrue(
                len(prerelease) > 0, "Prerelease component should not be empty"
            )


if __name__ == "__main__":
    unittest.main()
