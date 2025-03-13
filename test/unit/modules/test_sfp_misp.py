import pytest
import unittest

from modules.sfp_misp import sfp_misp
from spiderfoot import SpiderFootEvent, SpiderFootTarget


@pytest.mark.usefixtures
class TestModuleMisp(unittest.TestCase):
    """
    Test modules.sfp_misp
    """

    def test_opts(self):
        module = sfp_misp()
        self.assertEqual(len(module.opts), 7)

    def test_setup(self):
        """
        Test setup(self, sfc, userOpts=dict())
        """
        module = sfp_misp()
        module.setup(None, dict())
        self.assertIsNone(module.misp_event)
        self.assertEqual(module.scan_object_count, 0)

    def test_watchedEvents(self):
        module = sfp_misp()
        self.assertEqual(module.watchedEvents(), ["*"])

    def test_producedEvents(self):
        module = sfp_misp()
        self.assertEqual(module.producedEvents(), [])

    def test_handleEvent(self):
        """
        Test handleEvent(self, sfEvent)
        """
        module = sfp_misp()
        
        module.setup(None, dict())
        
        event_data = "example data"
        event_type = "ROOT"
        module_sfp = "sfp_test"
        source_event = ""
        
        event = SpiderFootEvent(
            event_type,
            event_data,
            module_sfp,
            source_event
        )
        
        # This event type should not be processed
        result = module.handleEvent(event)
        self.assertIsNone(result)
        
        # Try with a non-ROOT event
        event_type = "DOMAIN_NAME"
        event = SpiderFootEvent(
            event_type,
            event_data,
            module_sfp,
            source_event
        )
        
        # No MISP integration available so should return None
        result = module.handleEvent(event)
        self.assertIsNone(result)
