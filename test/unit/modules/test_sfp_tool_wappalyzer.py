from unittest.mock import patch, MagicMock

from modules.sfp_tool_wappalyzer import sfp_tool_wappalyzer
from spiderfoot.sflib import SpiderFoot
from spiderfoot import SpiderFootEvent, SpiderFootTarget
from test.unit.utils.test_base import TestModuleBase
from test.unit.utils.test_helpers import safe_recursion


class TestModuleWappalyzer(TestModuleBase):

    def test_opts(self: 'TestModuleWappalyzer') -> None:
        """Test that opts and optdescs have same length."""
        module = sfp_tool_wappalyzer()
        self.assertEqual(len(module.opts), len(module.optdescs))

    def test_setup(self: 'TestModuleWappalyzer') -> None:
        """Test module setup."""
        sf = SpiderFoot(self.default_options)
        module = sfp_tool_wappalyzer()
        module.setup(sf, dict())

    def test_watchedEvents_should_return_list(
        self: 'TestModuleWappalyzer',
    ) -> None:
        """Test watchedEvents returns a list."""
        module = sfp_tool_wappalyzer()
        self.assertIsInstance(module.watchedEvents(), list)

    def test_producedEvents_should_return_list(
        self: 'TestModuleWappalyzer',
    ) -> None:
        """Test producedEvents returns a list."""
        module = sfp_tool_wappalyzer()
        self.assertIsInstance(module.producedEvents(), list)

    @safe_recursion(max_depth=5)
    def test_handleEvent_no_tool_path_configured_should_set_errorState(
        self: 'TestModuleWappalyzer',
    ) -> None:
        """Test handleEvent sets errorState when no tool path."""
        sf = SpiderFoot(self.default_options)

        module = sfp_tool_wappalyzer()
        module.setup(sf, dict())

        target_value = 'example target value'
        target_type = 'IP_ADDRESS'
        target = SpiderFootTarget(target_value, target_type)
        module.setTarget(target)

        event_type = 'ROOT'
        event_data = 'example data'
        event_module = ''
        source_event = ''
        evt = SpiderFootEvent(event_type, event_data,
                              event_module, source_event)

        result = module.handleEvent(evt)

        self.assertIsNone(result)
        self.assertTrue(module.errorState)

    def setUp(self: 'TestModuleWappalyzer') -> None:
        """Set up before each test."""
        super().setUp()
        # Register event emitters if they exist
        if hasattr(self, 'module'):
            self.register_event_emitter(self.module)

    def tearDown(self: 'TestModuleWappalyzer') -> None:
        """Clean up after each test."""
        super().tearDown()


class TestModuleWappalyzerAPI(TestModuleBase):

    def setUp(self: 'TestModuleWappalyzerAPI') -> None:
        """Set up test fixtures for API tests."""
        super().setUp()
        self.sf = SpiderFoot({})
        self.module = sfp_tool_wappalyzer()
        self.target_value = 'example.com'
        self.target_type = 'INTERNET_NAME'
        self.target = SpiderFootTarget(
            self.target_value, self.target_type
        )
        self.event = SpiderFootEvent(
            'INTERNET_NAME', self.target_value,
            'sfp_tool_wappalyzer', None
        )
        self.module.setTarget(self.target)

    @patch(
        'modules.sfp_tool_wappalyzer.requests.get'
    )
    @patch(
        'modules.sfp_tool_wappalyzer'
        '.sfp_tool_wappalyzer.notifyListeners'
    )
    def test_handleEvent_success(
        self: 'TestModuleWappalyzerAPI',
        mock_notify: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Test successful handleEvent with API response.

        Args:
            mock_notify: Mocked notifyListeners method.
            mock_get: Mocked requests.get function.
        """
        opts = {
            'wappalyzer_api_key': 'FAKEKEY',
            'wappalyzer_api_url': (
                'https://api.wappalyzer.com/v2/lookup/'
            )
        }
        self.module.setup(self.sf, opts)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{
            'technologies': [
                {
                    'name': 'Apache',
                    'categories': [{'name': 'Web servers'}]
                },
                {
                    'name': 'Linux',
                    'categories': [
                        {'name': 'Operating systems'}
                    ]
                },
                {
                    'name': 'jQuery',
                    'categories': [
                        {'name': 'JavaScript frameworks'}
                    ]
                }
            ]
        }]
        mock_get.return_value = mock_resp
        self.module.handleEvent(self.event)
        self.assertTrue(mock_notify.called)
        calls = [
            call[0][0].eventType
            for call in mock_notify.call_args_list
        ]
        self.assertIn('WEBSERVER_TECHNOLOGY', calls)
        self.assertIn('OPERATING_SYSTEM', calls)
        self.assertIn('SOFTWARE_USED', calls)

    @patch(
        'modules.sfp_tool_wappalyzer.requests.get'
    )
    def test_handleEvent_api_error(
        self: 'TestModuleWappalyzerAPI',
        mock_get: MagicMock,
    ) -> None:
        """Test handleEvent with API error response.

        Args:
            mock_get: Mocked requests.get function.
        """
        opts = {
            'wappalyzer_api_key': 'FAKEKEY',
            'wappalyzer_api_url': (
                'https://api.wappalyzer.com/v2/lookup/'
            )
        }
        self.module.setup(self.sf, opts)
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = 'Forbidden'
        mock_get.return_value = mock_resp
        self.module.handleEvent(self.event)
        self.assertTrue(
            self.module.errorState
            or not self.module.results[self.target_value]
        )

    def test_handleEvent_no_api_key(
        self: 'TestModuleWappalyzerAPI',
    ) -> None:
        """Test handleEvent with no API key configured."""
        opts = {'wappalyzer_api_key': ''}
        self.module.setup(self.sf, opts)
        self.module.handleEvent(self.event)
        self.assertTrue(self.module.errorState)

    @patch(
        'modules.sfp_tool_wappalyzer.requests.get'
    )
    def test_handleEvent_no_technologies(
        self: 'TestModuleWappalyzerAPI',
        mock_get: MagicMock,
    ) -> None:
        """Test handleEvent with no technologies in response.

        Args:
            mock_get: Mocked requests.get function.
        """
        opts = {
            'wappalyzer_api_key': 'FAKEKEY',
            'wappalyzer_api_url': (
                'https://api.wappalyzer.com/v2/lookup/'
            )
        }
        self.module.setup(self.sf, opts)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{}]
        mock_get.return_value = mock_resp
        self.module.handleEvent(self.event)
        self.assertFalse(self.module.errorState)

# End of API unit tests
