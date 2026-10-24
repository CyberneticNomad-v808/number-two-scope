"""
Regression tests for database settings persistence bug.
Tests that module settings (specifically sfp__stor_db PostgreSQL settings)
are properly saved to and loaded from the database.

NOTE: SQLite support has been removed. These tests need PostgreSQL mocking.
"""
import pytest
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch
import json

# Skip all tests - SQLite support removed, tests need PostgreSQL mocking
pytestmark = pytest.mark.skip(reason="SQLite support removed - tests need PostgreSQL mocking")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from spiderfoot import SpiderFootDb, SpiderFoot, SpiderFootHelpers
from spiderfoot.sflib import configSerialize, configUnserialize


class TestDatabaseSettingsPersistence:
    """Test that database settings persist correctly."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database and config for each test."""
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db.close()

        # Load modules
        mod_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'modules')
        self.modules = SpiderFootHelpers.loadModulesAsDict(mod_dir, ['sfp_template.py'])

        self.defaultConfig = {
            '__modules__': self.modules,
            '__database': self.test_db.name
        }

        # Initialize database
        self.dbh = SpiderFootDb(self.defaultConfig, init=True)
        self.sf = SpiderFoot(self.defaultConfig)

        yield

        # Cleanup
        try:
            os.unlink(self.test_db.name)
        except:
            pass

    def test_module_settings_save(self):
        """Test that module settings are saved to database correctly."""
        # Define test settings
        test_settings = {
            'sfp__stor_db:postgresql_host': 'testhost.local',
            'sfp__stor_db:postgresql_port': '5433',
            'sfp__stor_db:postgresql_database': 'testdb',
            'sfp__stor_db:postgresql_username': 'testuser',
            'sfp__stor_db:postgresql_password': 'testpass',
            'sfp__stor_db:db_type': 'postgresql'
        }

        # Save settings
        self.dbh.configSet(test_settings)

        # Retrieve settings
        saved_config = self.dbh.configGet()

        # Verify all settings were saved
        for key, value in test_settings.items():
            assert key in saved_config, f"Setting {key} was not saved"
            assert saved_config[key] == value, f"Setting {key} has wrong value: {saved_config[key]} != {value}"

    def test_module_settings_unserialize(self):
        """Test that module settings are properly unserialized."""
        # Define test settings
        test_settings = {
            'sfp__stor_db:postgresql_host': 'testhost.local',
            'sfp__stor_db:postgresql_port': '5433',
            'sfp__stor_db:postgresql_database': 'testdb',
            'sfp__stor_db:postgresql_username': 'testuser',
            'sfp__stor_db:postgresql_password': 'testpass',
            'sfp__stor_db:db_type': 'postgresql'
        }

        # Save and retrieve settings
        self.dbh.configSet(test_settings)
        saved_config = self.dbh.configGet()

        # Unserialize with modules loaded
        unserialized = self.sf.configUnserialize(saved_config, self.defaultConfig)

        # Verify module exists in unserialized config
        assert '__modules__' in unserialized, "__modules__ not in unserialized config"
        assert 'sfp__stor_db' in unserialized['__modules__'], "sfp__stor_db module not found"

        # Get module options
        module_opts = unserialized['__modules__']['sfp__stor_db'].get('opts', {})

        # Verify each setting was unserialized correctly
        assert module_opts['postgresql_host'] == 'testhost.local'
        assert module_opts['postgresql_port'] == 5433  # Should be int
        assert module_opts['postgresql_database'] == 'testdb'
        assert module_opts['postgresql_username'] == 'testuser'
        assert module_opts['postgresql_password'] == 'testpass'
        assert module_opts['db_type'] == 'postgresql'

    def test_webui_routes_config_loading_order(self):
        """Test that WebUI routes loads modules before unserializing config."""
        from spiderfoot.webui.routes import WebUiRoutes

        # Save some module settings to database
        test_settings = {
            'sfp__stor_db:postgresql_host': 'production.db.server',
            'sfp__stor_db:postgresql_port': '5432',
            'sfp__stor_db:postgresql_database': 'spiderfoot_prod'
        }
        self.dbh.configSet(test_settings)

        # Create WebUiRoutes instance
        web_config = {'root': '/'}
        routes = WebUiRoutes(web_config, self.defaultConfig)

        # Verify modules are loaded
        assert '__modules__' in routes.config, "__modules__ not loaded in routes config"
        assert 'sfp__stor_db' in routes.config['__modules__'], "sfp__stor_db not in loaded modules"

        # Verify saved settings were loaded
        module_opts = routes.config['__modules__']['sfp__stor_db'].get('opts', {})
        assert module_opts['postgresql_host'] == 'production.db.server'
        assert module_opts['postgresql_port'] == 5432
        assert module_opts['postgresql_database'] == 'spiderfoot_prod'

    def test_settings_persistence_across_restarts(self):
        """Test that settings persist across application restarts."""
        # Save settings
        test_settings = {
            'sfp__stor_db:postgresql_host': 'persist.test.host',
            'sfp__stor_db:postgresql_port': '15432',
            'sfp__stor_db:postgresql_username': 'persist_user'
        }
        self.dbh.configSet(test_settings)

        # Simulate restart by creating new instances
        dbh2 = SpiderFootDb(self.defaultConfig, init=False)
        sf2 = SpiderFoot(self.defaultConfig)

        # Load config
        loaded_config = dbh2.configGet()
        unserialized = sf2.configUnserialize(loaded_config, self.defaultConfig)

        # Verify settings persisted
        module_opts = unserialized['__modules__']['sfp__stor_db']['opts']
        assert module_opts['postgresql_host'] == 'persist.test.host'
        assert module_opts['postgresql_port'] == 15432
        assert module_opts['postgresql_username'] == 'persist_user'

    def test_partial_module_settings_update(self):
        """Test updating only some module settings."""
        # Set initial settings
        initial_settings = {
            'sfp__stor_db:postgresql_host': 'initial.host',
            'sfp__stor_db:postgresql_port': '5432',
            'sfp__stor_db:postgresql_database': 'initial_db'
        }
        self.dbh.configSet(initial_settings)

        # Update only host
        update_settings = {
            'sfp__stor_db:postgresql_host': 'updated.host'
        }
        self.dbh.configSet(update_settings)

        # Load and check
        loaded_config = self.dbh.configGet()
        unserialized = self.sf.configUnserialize(loaded_config, self.defaultConfig)
        module_opts = unserialized['__modules__']['sfp__stor_db']['opts']

        assert module_opts['postgresql_host'] == 'updated.host', "Host not updated"
        assert module_opts['postgresql_port'] == 5432, "Port should remain unchanged"
        assert module_opts['postgresql_database'] == 'initial_db', "Database should remain unchanged"

    def test_serialize_deserialize_roundtrip(self):
        """Test that serialize/deserialize is symmetric."""
        # Start with modules that have some custom settings
        test_config = self.defaultConfig.copy()
        test_config['__modules__']['sfp__stor_db']['opts']['postgresql_host'] = 'roundtrip.host'
        test_config['__modules__']['sfp__stor_db']['opts']['postgresql_port'] = 9999
        test_config['__modules__']['sfp__stor_db']['opts']['db_type'] = 'postgresql'

        # Serialize
        serialized = configSerialize(test_config, filterSystem=False)

        # Save to DB
        self.dbh.configSet(serialized)

        # Load from DB
        loaded = self.dbh.configGet()

        # Deserialize
        deserialized = configUnserialize(loaded, self.defaultConfig, filterSystem=False)

        # Check roundtrip
        module_opts = deserialized['__modules__']['sfp__stor_db']['opts']
        assert module_opts['postgresql_host'] == 'roundtrip.host'
        assert module_opts['postgresql_port'] == 9999
        assert module_opts['db_type'] == 'postgresql'


class TestBooleanSettingsPersistence:
    """Test boolean settings persistence specifically."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database and config for each test."""
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db.close()

        # Load modules
        mod_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'modules')
        self.modules = SpiderFootHelpers.loadModulesAsDict(mod_dir, ['sfp_template.py'])

        self.defaultConfig = {
            '__modules__': self.modules,
            '__database': self.test_db.name,
            '_debug': False  # Global boolean setting
        }

        # Initialize database
        self.dbh = SpiderFootDb(self.defaultConfig, init=True)
        self.sf = SpiderFoot(self.defaultConfig)

        yield

        # Cleanup
        try:
            os.unlink(self.test_db.name)
        except:
            pass

    def test_boolean_module_settings(self):
        """Test that boolean module settings persist correctly."""
        # Save boolean settings
        test_settings = {
            'sfp__stor_db:enable_auto_recovery': '1',  # True as string
            'sfp__stor_db:enable_connection_monitoring': '0',  # False as string
            '_debug': '1'  # Global boolean
        }
        self.dbh.configSet(test_settings)

        # Load and unserialize
        loaded_config = self.dbh.configGet()
        unserialized = self.sf.configUnserialize(loaded_config, self.defaultConfig)

        # Check module booleans
        module_opts = unserialized['__modules__']['sfp__stor_db']['opts']
        assert module_opts['enable_auto_recovery'] == True
        assert module_opts['enable_connection_monitoring'] == False

        # Check global boolean
        assert unserialized['_debug'] == True


class TestBugVerification:
    """Tests that explicitly verify the bug would be caught and the fix works."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database and config for each test."""
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db.close()

        # Load modules
        mod_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'modules')
        self.modules = SpiderFootHelpers.loadModulesAsDict(mod_dir, ['sfp_template.py'])

        self.defaultConfig = {
            '__modules__': self.modules,
            '__database': self.test_db.name
        }

        # Initialize database
        self.dbh = SpiderFootDb(self.defaultConfig, init=True)
        self.sf = SpiderFoot(self.defaultConfig)

        yield

        # Cleanup
        try:
            os.unlink(self.test_db.name)
        except:
            pass

    def test_original_bug_modules_not_loaded_first(self):
        """
        Reproduce the original bug: if modules are NOT loaded before
        configUnserialize, module settings are not properly restored.

        This test verifies the bug that was fixed would be caught.
        """
        # Save settings to database
        test_settings = {
            'sfp__stor_db:postgresql_host': 'bug.test.host',
            'sfp__stor_db:postgresql_port': '5432',
            'sfp__stor_db:postgresql_database': 'bug_db',
            'sfp__stor_db:postgresql_username': 'bug_user'
        }
        self.dbh.configSet(test_settings)

        # Load config from DB
        saved_config = self.dbh.configGet()

        # Verify settings are in database
        assert 'sfp__stor_db:postgresql_host' in saved_config
        assert saved_config['sfp__stor_db:postgresql_host'] == 'bug.test.host'

        # Try to unserialize WITHOUT modules loaded (reproducing bug)
        config_without_modules = {'__database': self.test_db.name}
        # Note: NO '__modules__' in referencePoint

        # This should fail to restore module settings properly
        result = configUnserialize(saved_config, config_without_modules)

        # Verify the bug: module settings are lost
        # When modules aren't loaded, there's no reference point for module settings
        if '__modules__' in result and 'sfp__stor_db' in result['__modules__']:
            # If module exists, check if settings were actually restored
            opts = result['__modules__']['sfp__stor_db'].get('opts', {})
            if opts.get('postgresql_host') == 'bug.test.host':
                pytest.fail("Bug not reproduced - module settings should be lost without modules loaded")

        # Now verify the fix: WITH modules loaded
        config_with_modules = self.defaultConfig.copy()
        result_fixed = configUnserialize(saved_config, config_with_modules)

        # Verify fix: module settings are restored
        assert '__modules__' in result_fixed, "__modules__ not in unserialized config"
        assert 'sfp__stor_db' in result_fixed['__modules__'], "sfp__stor_db module not found"
        assert result_fixed['__modules__']['sfp__stor_db']['opts']['postgresql_host'] == 'bug.test.host'
        assert result_fixed['__modules__']['sfp__stor_db']['opts']['postgresql_port'] == 5432
        assert result_fixed['__modules__']['sfp__stor_db']['opts']['postgresql_database'] == 'bug_db'

    def test_module_loading_order_in_webui_routes(self):
        """
        Verify that WebUiRoutes loads modules BEFORE attempting to
        unserialize config from database.

        This is a critical test of the fix implementation.
        """
        from spiderfoot.webui.routes import WebUiRoutes

        # Save settings to database first
        test_settings = {
            'sfp__stor_db:postgresql_host': 'order.test.host',
            'sfp__stor_db:postgresql_port': '7777'
        }
        self.dbh.configSet(test_settings)

        # Create WebUiRoutes instance - this is where the fix is
        web_config = {'root': '/'}
        routes = WebUiRoutes(web_config, self.defaultConfig)

        # Verify that:
        # 1. Modules are loaded
        assert '__modules__' in routes.config, "__modules__ not loaded"
        assert 'sfp__stor_db' in routes.config['__modules__'], "sfp__stor_db not loaded"

        # 2. Module has default structure
        assert 'opts' in routes.config['__modules__']['sfp__stor_db'], "Module opts not present"

        # 3. Saved settings were properly restored
        module_opts = routes.config['__modules__']['sfp__stor_db']['opts']
        assert module_opts['postgresql_host'] == 'order.test.host', \
            f"Settings not restored. Expected 'order.test.host', got '{module_opts.get('postgresql_host')}'"
        assert module_opts['postgresql_port'] == 7777, \
            f"Settings not restored. Expected 7777, got {module_opts.get('postgresql_port')}"

    @patch('spiderfoot.webui.routes.SpiderFootHelpers.loadModulesAsDict')
    def test_modules_loaded_before_database_config_restored(self, mock_load_modules):
        """
        Use mocking to verify modules are loaded BEFORE database config is read.
        This tests the fix at a more granular level.
        """
        from spiderfoot.webui.routes import WebUiRoutes

        # Track whether modules were loaded before DB was accessed
        load_order = []

        def track_load_modules(*args, **kwargs):
            load_order.append('load_modules')
            return self.modules

        mock_load_modules.side_effect = track_load_modules

        # Patch SpiderFootDb to track when it's called
        original_db_init = SpiderFootDb.__init__

        def track_db_init(instance, *args, **kwargs):
            load_order.append('db_init')
            return original_db_init(instance, *args, **kwargs)

        with patch.object(SpiderFootDb, '__init__', track_db_init):
            web_config = {'root': '/'}
            routes = WebUiRoutes(web_config, self.defaultConfig)

        # Verify order: modules must be loaded before database
        assert load_order[0] == 'load_modules', \
            f"Modules not loaded first! Order was: {load_order}"
        assert load_order[1] == 'db_init', \
            f"Database not initialized after modules! Order was: {load_order}"


class TestErrorConditions:
    """Test error conditions and edge cases."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database and config for each test."""
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db.close()

        # Load modules
        mod_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'modules')
        self.modules = SpiderFootHelpers.loadModulesAsDict(mod_dir, ['sfp_template.py'])

        self.defaultConfig = {
            '__modules__': self.modules,
            '__database': self.test_db.name
        }

        # Initialize database
        self.dbh = SpiderFootDb(self.defaultConfig, init=True)
        self.sf = SpiderFoot(self.defaultConfig)

        yield

        # Cleanup
        try:
            os.unlink(self.test_db.name)
        except:
            pass

    def test_invalid_type_conversion_handled_gracefully(self):
        """
        Test that invalid data types in database don't crash unserialization.
        """
        # Manually insert invalid data into database
        try:
            with self.dbh.dbhLock:
                self.dbh.dbh.execute(
                    "INSERT OR REPLACE INTO tbl_config (scope, opt, val) VALUES (?, ?, ?)",
                    ('sfp__stor_db', 'postgresql_port', 'not_a_number')
                )
                self.dbh.conn.commit()
        except AttributeError:
            # Different database access pattern
            self.dbh.dbh.execute(
                "INSERT OR REPLACE INTO tbl_config (scope, opt, val) VALUES (?, ?, ?)",
                ('sfp__stor_db', 'postgresql_port', 'not_a_number')
            )
            self.dbh.dbh.commit()

        # Try to load config
        loaded_config = self.dbh.configGet()

        # Should handle error gracefully
        try:
            unserialized = self.sf.configUnserialize(loaded_config, self.defaultConfig)
            # Should either use default value or raise clear error
            module_opts = unserialized['__modules__']['sfp__stor_db']['opts']
            # Should fallback to default or convert properly
            port_value = module_opts.get('postgresql_port')
            # Accept either default value or ValueError
            if port_value != 5432:  # default
                pytest.fail(f"Expected ValueError or default value, got {port_value}")
        except ValueError as e:
            # Or should provide clear error message
            assert 'postgresql_port' in str(e).lower() or 'int' in str(e).lower()

    def test_empty_module_settings(self):
        """Test behavior with empty module settings."""
        # Test with no additional settings (just use defaults)

        # Load and unserialize
        loaded_config = self.dbh.configGet()
        unserialized = self.sf.configUnserialize(loaded_config, self.defaultConfig)

        # Should still have default module structure
        assert '__modules__' in unserialized
        assert 'sfp__stor_db' in unserialized['__modules__']

        # Should have default values
        module_opts = unserialized['__modules__']['sfp__stor_db']['opts']
        assert module_opts['postgresql_host'] == 'localhost'  # default
        assert module_opts['postgresql_port'] == 5432  # default

    def test_malformed_module_name_in_settings(self):
        """Test handling of malformed module names in saved settings."""
        # Save setting with malformed module name
        test_settings = {
            'nonexistent_module:some_option': 'value',
            'sfp__stor_db:postgresql_host': 'valid.host'
        }
        self.dbh.configSet(test_settings)

        # Should not crash
        loaded_config = self.dbh.configGet()
        unserialized = self.sf.configUnserialize(loaded_config, self.defaultConfig)

        # Valid setting should still work
        assert unserialized['__modules__']['sfp__stor_db']['opts']['postgresql_host'] == 'valid.host'

    @pytest.mark.parametrize("test_value", [
        "host-with-ünïcödé",
        "host'with'quotes",
        'host"with"doublequotes',
        "host with spaces",
        "host;with;semicolons",
        "🚀emoji_host🎉"
    ])
    def test_special_characters_in_settings(self, test_value):
        """Test settings with special characters persist correctly."""
        test_settings = {
            'sfp__stor_db:postgresql_host': test_value,
        }
        self.dbh.configSet(test_settings)

        loaded_config = self.dbh.configGet()
        unserialized = self.sf.configUnserialize(loaded_config, self.defaultConfig)

        module_opts = unserialized['__modules__']['sfp__stor_db']['opts']
        assert module_opts['postgresql_host'] == test_value, \
            f"Special characters not preserved: expected '{test_value}', got '{module_opts['postgresql_host']}'"

    def test_null_values_in_settings(self):
        """Test handling of null/None values in settings."""
        test_settings = {
            'sfp__stor_db:postgresql_password': '',  # Empty string
        }
        self.dbh.configSet(test_settings)

        loaded_config = self.dbh.configGet()
        unserialized = self.sf.configUnserialize(loaded_config, self.defaultConfig)

        module_opts = unserialized['__modules__']['sfp__stor_db']['opts']
        assert module_opts['postgresql_password'] == '', "Empty string not preserved"

    def test_very_long_setting_value(self):
        """Test handling of very long setting values."""
        long_value = 'a' * 10000  # 10KB string
        test_settings = {
            'sfp__stor_db:postgresql_host': long_value,
        }
        self.dbh.configSet(test_settings)

        loaded_config = self.dbh.configGet()
        unserialized = self.sf.configUnserialize(loaded_config, self.defaultConfig)

        module_opts = unserialized['__modules__']['sfp__stor_db']['opts']
        assert module_opts['postgresql_host'] == long_value, "Long value not preserved"
        assert len(module_opts['postgresql_host']) == 10000


class TestIntegration:
    """Integration tests for the full settings persistence flow."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database and config for each test."""
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db.close()

        # Load modules
        mod_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'modules')
        self.modules = SpiderFootHelpers.loadModulesAsDict(mod_dir, ['sfp_template.py'])

        self.defaultConfig = {
            '__modules__': self.modules,
            '__database': self.test_db.name
        }

        # Initialize database
        self.dbh = SpiderFootDb(self.defaultConfig, init=True)
        self.sf = SpiderFoot(self.defaultConfig)

        yield

        # Cleanup
        try:
            os.unlink(self.test_db.name)
        except:
            pass

    def test_full_save_and_load_cycle(self):
        """
        Test the complete cycle:
        1. Start with defaults
        2. Save custom settings
        3. Restart application (new instances)
        4. Verify custom settings loaded
        """
        # Step 1: Verify defaults
        assert self.defaultConfig['__modules__']['sfp__stor_db']['opts']['postgresql_host'] == 'localhost'

        # Step 2: Save custom settings
        custom_settings = {
            'sfp__stor_db:postgresql_host': 'production.db.server',
            'sfp__stor_db:postgresql_port': '5433',
            'sfp__stor_db:postgresql_database': 'spiderfoot_prod',
            'sfp__stor_db:postgresql_username': 'prod_user',
            'sfp__stor_db:db_type': 'postgresql'
        }
        self.dbh.configSet(custom_settings)

        # Step 3: Simulate restart - create new instances
        dbh2 = SpiderFootDb(self.defaultConfig, init=False)
        sf2 = SpiderFoot(self.defaultConfig)

        # Step 4: Load and verify
        loaded_config = dbh2.configGet()
        final_config = sf2.configUnserialize(loaded_config, self.defaultConfig)

        # Verify all custom settings persisted
        module_opts = final_config['__modules__']['sfp__stor_db']['opts']
        assert module_opts['postgresql_host'] == 'production.db.server'
        assert module_opts['postgresql_port'] == 5433
        assert module_opts['postgresql_database'] == 'spiderfoot_prod'
        assert module_opts['postgresql_username'] == 'prod_user'
        assert module_opts['db_type'] == 'postgresql'

    def test_multiple_modules_settings_persist(self):
        """Test that settings for multiple modules all persist correctly."""
        # Save settings for multiple modules
        test_settings = {
            'sfp__stor_db:postgresql_host': 'db.server',
            'sfp__stor_db:postgresql_port': '5432',
            # Add other module settings if available
        }
        self.dbh.configSet(test_settings)

        # Load and verify
        loaded_config = self.dbh.configGet()
        unserialized = self.sf.configUnserialize(loaded_config, self.defaultConfig)

        # Verify sfp__stor_db settings
        stor_db_opts = unserialized['__modules__']['sfp__stor_db']['opts']
        assert stor_db_opts['postgresql_host'] == 'db.server'
        assert stor_db_opts['postgresql_port'] == 5432

    def test_webui_routes_with_pre_saved_settings(self):
        """
        Test WebUiRoutes initialization with pre-existing saved settings.
        This is the real-world scenario.
        """
        from spiderfoot.webui.routes import WebUiRoutes

        # Step 1: Save settings (simulating previous user configuration)
        test_settings = {
            'sfp__stor_db:postgresql_host': 'configured.host',
            'sfp__stor_db:postgresql_port': '9999',
            'sfp__stor_db:postgresql_database': 'configured_db',
            '_debug': '1'
        }
        self.dbh.configSet(test_settings)

        # Step 2: Create WebUiRoutes (simulating application start)
        web_config = {'root': '/'}
        routes = WebUiRoutes(web_config, self.defaultConfig)

        # Step 3: Verify routes.config has saved settings
        module_opts = routes.config['__modules__']['sfp__stor_db']['opts']
        assert module_opts['postgresql_host'] == 'configured.host', \
            "WebUiRoutes did not load saved module settings"
        assert module_opts['postgresql_port'] == 9999, \
            "WebUiRoutes did not load saved module settings"
        assert module_opts['postgresql_database'] == 'configured_db', \
            "WebUiRoutes did not load saved module settings"

        # Global setting might not be in the config if not part of default
        # This is OK - module settings are the focus of this test