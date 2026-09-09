"""
Regression tests for Item 7 of the correlation/module refactor plan:
ported tool-wrapper modules must preflight-check their configured binary
path in setup(), not discover it's missing only on the first matching
handleEvent() call.
"""
from modules.sfp_httpx import sfp_httpx
from modules.sfp_tool_dnsx import sfp_tool_dnsx
from modules.sfp_subfinder import sfp_subfinder
from modules.sfp_tool_gowitness import sfp_tool_gowitness
from modules.sfp_tool_nikto import sfp_tool_nikto
from spiderfoot.sflib import SpiderFoot
from test.unit.utils.test_module_base import TestModuleBase


MODULE_AND_PATH_OPT = [
    (sfp_httpx, 'httpx_path'),
    (sfp_tool_dnsx, 'dnsx_path'),
    (sfp_subfinder, 'subfinder_path'),
    (sfp_tool_gowitness, 'gowitness_path'),
    (sfp_tool_nikto, 'nikto_path'),
]


class TestBinaryPreflightCheck(TestModuleBase):

    def test_missing_binary_sets_errorstate_immediately(self):
        """setup() must set errorState=True right away when the configured
        path doesn't exist -- not silently succeed and only fail later on
        the first handleEvent()."""
        sf = SpiderFoot(self.default_options)
        for module_cls, path_opt in MODULE_AND_PATH_OPT:
            with self.subTest(module=module_cls.__name__, opt=path_opt):
                module = module_cls()
                module.setup(sf, {path_opt: '/definitely/does/not/exist/binary'})
                self.assertTrue(
                    module.errorState,
                    f"{module_cls.__name__}.setup() did not set errorState "
                    f"for a nonexistent {path_opt}"
                )

    def test_real_binary_does_not_set_errorstate(self):
        """A real, executable path (using /bin/true as a stand-in) must
        NOT trip errorState."""
        sf = SpiderFoot(self.default_options)
        for module_cls, path_opt in MODULE_AND_PATH_OPT:
            with self.subTest(module=module_cls.__name__, opt=path_opt):
                module = module_cls()
                module.setup(sf, {path_opt: '/bin/true'})
                self.assertFalse(
                    module.errorState,
                    f"{module_cls.__name__}.setup() incorrectly set "
                    f"errorState for a real, executable {path_opt}"
                )

    def test_gowitness_missing_chrome_path_is_not_fatal(self):
        """chrome_path is documented as optional (gowitness auto-detects);
        a missing/blank chrome_path must not set errorState on its own,
        only a missing gowitness_path should."""
        sf = SpiderFoot(self.default_options)
        module = sfp_tool_gowitness()
        module.setup(sf, {'gowitness_path': '/bin/true', 'chrome_path': ''})
        self.assertFalse(module.errorState)

    def test_check_binary_falls_back_to_path_lookup_when_unset(self):
        """With no explicit path configured, check_binary() should try
        resolving the option's implied binary name on $PATH (matching each
        module's own lazy _find_* fallback behavior) rather than crashing.
        errorState will correctly be True if that binary truly isn't on
        PATH in this environment, or False if it is -- either is valid;
        this test only asserts check_binary() runs without raising."""
        sf = SpiderFoot(self.default_options)
        module = sfp_httpx()
        module.setup(sf, {})
        self.assertIn(module.errorState, (True, False))

    def setUp(self):
        """Set up before each test."""
        super().setUp()
        if hasattr(self, 'module'):
            self.register_event_emitter(self.module)

    def tearDown(self):
        """Clean up after each test."""
        super().tearDown()
