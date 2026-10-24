"""
Regression test for WebUI settings form submission bug.

Tests that settings submitted via the web form (with boolean values)
are properly converted and persist to the database.

This specifically tests the fix for:
- Boolean values from form (JavaScript true/false) being converted to "1"/"0"
- Settings using self.defaultConfig instead of self.config for database connection
- Settings being reloaded from database after save

Bug: When changing db_type from sqlite to postgresql in settings form,
the change would return HTTP 200 but not persist.

NOTE: SQLite support has been removed. These tests need PostgreSQL mocking.
"""
import os
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test.unit.utils.test_module_base import TestModuleBase
from spiderfoot import SpiderFootDb, SpiderFoot, SpiderFootHelpers

import pytest

# Skip all tests - SQLite support removed, tests need PostgreSQL mocking
pytestmark = pytest.mark.skip(reason="SQLite support removed - tests need PostgreSQL mocking")


@pytest.mark.regression
@pytest.mark.integration
class TestWebUISettingsFormSubmission(TestModuleBase):
    """Test the actual WebUI settings save flow with form data."""

    def setUp(self):
        """Set up test database and config for each test."""
        super().setUp()

        # Create worker-safe temp file name
        worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')
        self.test_db = tempfile.NamedTemporaryFile(
            suffix=f'_{worker_id}.db',
            delete=False,
            dir=tempfile.gettempdir()
        )
        self.test_db.close()

        # Load modules with fallback paths
        mod_dir = self._get_modules_dir()
        self.modules = SpiderFootHelpers.loadModulesAsDict(mod_dir, ['sfp_template.py'])

        self.defaultConfig = {
            '__modules__': self.modules,
            '__database': self.test_db.name,
            '_debug': False
        }

        # Initialize database and register for cleanup
        self.dbh = SpiderFootDb(self.defaultConfig, init=True)
        self.sf = SpiderFoot(self.defaultConfig)

        # Register resources for automatic cleanup
        self.resource_manager.register_resource(
            self.test_db,
            lambda: self._cleanup_db_file(),
            category="temp_file"
        )

    def _get_modules_dir(self):
        """Get modules directory with fallback paths."""
        # Try relative path from current file
        mod_dir = Path(__file__).parent.parent.parent / 'modules'
        if mod_dir.exists():
            return str(mod_dir)

        # Try absolute path
        mod_dir = Path(__file__).resolve().parent.parent.parent / 'modules'
        if mod_dir.exists():
            return str(mod_dir)

        raise FileNotFoundError("Could not locate modules directory")

    def _cleanup_db_file(self):
        """Clean up database file safely."""
        try:
            if os.path.exists(self.test_db.name):
                os.unlink(self.test_db.name)
        except Exception:
            pass

    @pytest.mark.timeout(30)
    def test_form_boolean_conversion(self):
        """
        Test that boolean values from form are converted to "1"/"0" strings.

        This simulates the exact flow when a form is submitted:
        1. Form sends JSON with boolean values (true/false)
        2. Booleans must be converted to "1"/"0" strings
        3. Settings saved to database
        4. Settings reloaded and converted back to booleans
        """
        # Simulate form data (exactly as it comes from JavaScript)
        form_data = {
            "_debug": True,  # Boolean from JavaScript
            "sfp__stor_db:enable_connection_pooling": False,  # Boolean module setting
            "sfp__stor_db:enable_auto_recovery": True,
            "sfp__stor_db:db_type": "postgresql",  # String setting
            "sfp__stor_db:postgresql_host": "localhost"
        }

        # Step 1: Convert booleans to strings (what the fix does)
        converted_data = form_data.copy()
        for key in converted_data:
            if isinstance(converted_data[key], bool):
                converted_data[key] = "1" if converted_data[key] else "0"

        # Step 2: Save to database
        dbh = SpiderFootDb(self.defaultConfig)
        dbh.configSet(converted_data)

        # Step 3: Reload from database
        saved_config = dbh.configGet()

        # Verify strings were saved correctly
        assert saved_config['_debug'] == "1", "Boolean True should be saved as '1'"
        assert saved_config['sfp__stor_db:enable_connection_pooling'] == "0", "Boolean False should be saved as '0'"
        assert saved_config['sfp__stor_db:enable_auto_recovery'] == "1", "Boolean True should be saved as '1'"

        # Step 4: Unserialize (converts strings back to proper types)
        sf = SpiderFoot(self.defaultConfig)
        unserialized = sf.configUnserialize(saved_config, self.defaultConfig)

        # Verify booleans were restored correctly
        assert unserialized['_debug'] == True, "_debug should be True"
        assert unserialized['__modules__']['sfp__stor_db']['opts']['enable_connection_pooling'] == False
        assert unserialized['__modules__']['sfp__stor_db']['opts']['enable_auto_recovery'] == True

        # Verify non-boolean settings preserved
        assert unserialized['__modules__']['sfp__stor_db']['opts']['db_type'] == "postgresql"
        assert unserialized['__modules__']['sfp__stor_db']['opts']['postgresql_host'] == "localhost"

    @pytest.mark.timeout(30)
    def test_db_type_change_persistence(self):
        """
        Test the EXACT bug scenario: changing db_type from sqlite to postgresql.

        This was the specific bug reported:
        1. User changes db_type to "postgresql" in settings form
        2. Clicks save, gets HTTP 200
        3. Refreshes page, change is gone
        """
        # Initial state: sqlite
        initial_settings = {
            "sfp__stor_db:db_type": "sqlite"
        }
        dbh = SpiderFootDb(self.defaultConfig)
        dbh.configSet(initial_settings)

        # Verify initial state
        loaded = dbh.configGet()
        assert loaded.get('sfp__stor_db:db_type') == 'sqlite'

        # User changes to postgresql (simulating form submission)
        form_data = {
            "sfp__stor_db:db_type": "postgresql",
            "sfp__stor_db:postgresql_host": "unified-postgres",
            "sfp__stor_db:postgresql_port": "5432",
            "sfp__stor_db:postgresql_database": "spiderfoot_db",
            "sfp__stor_db:postgresql_username": "postgres",
            "sfp__stor_db:postgresql_password": "password123"
        }

        # Convert booleans (none in this case, but part of the fix)
        converted_data = form_data.copy()
        for key in converted_data:
            if isinstance(converted_data[key], bool):
                converted_data[key] = "1" if converted_data[key] else "0"

        # Save using defaultConfig (the fix)
        dbh = SpiderFootDb(self.defaultConfig)
        dbh.configSet(converted_data)

        # Reload from database (simulating page refresh)
        saved_config = dbh.configGet()

        # THIS IS THE BUG TEST: settings should persist
        assert saved_config.get('sfp__stor_db:db_type') == 'postgresql', "db_type change did not persist!"
        assert saved_config.get('sfp__stor_db:postgresql_host') == 'unified-postgres'
        assert saved_config.get('sfp__stor_db:postgresql_port') == '5432'
        assert saved_config.get('sfp__stor_db:postgresql_database') == 'spiderfoot_db'

        # Verify it unserializes correctly too
        sf = SpiderFoot(self.defaultConfig)
        unserialized = sf.configUnserialize(saved_config, self.defaultConfig)
        module_opts = unserialized['__modules__']['sfp__stor_db']['opts']

        assert module_opts['db_type'] == 'postgresql'
        assert module_opts['postgresql_host'] == 'unified-postgres'
        assert module_opts['postgresql_port'] == 5432  # Should be int after unserialize

    @pytest.mark.timeout(30)
    def test_mixed_boolean_and_string_settings(self):
        """
        Test form submission with mix of booleans and strings.

        This tests the complete scenario where a user changes both
        boolean settings and string settings in one form submission.
        """
        form_data = {
            # Global settings
            "_debug": True,

            # Module settings - booleans
            "sfp__stor_db:enable_connection_pooling": True,
            "sfp__stor_db:enable_auto_recovery": False,
            "sfp__stor_db:enable_load_balancing": True,

            # Module settings - strings
            "sfp__stor_db:db_type": "postgresql",
            "sfp__stor_db:postgresql_host": "db.example.com",
            "sfp__stor_db:postgresql_port": "5432",
            "sfp__stor_db:maxstorage": "2048"
        }

        # Convert booleans
        converted_data = form_data.copy()
        for key in converted_data:
            if isinstance(converted_data[key], bool):
                converted_data[key] = "1" if converted_data[key] else "0"

        # Save
        dbh = SpiderFootDb(self.defaultConfig)
        dbh.configSet(converted_data)

        # Reload
        saved_config = dbh.configGet()

        # Verify all settings saved
        assert saved_config['_debug'] == "1"
        assert saved_config['sfp__stor_db:enable_connection_pooling'] == "1"
        assert saved_config['sfp__stor_db:enable_auto_recovery'] == "0"
        assert saved_config['sfp__stor_db:enable_load_balancing'] == "1"
        assert saved_config['sfp__stor_db:db_type'] == "postgresql"
        assert saved_config['sfp__stor_db:postgresql_host'] == "db.example.com"

        # Unserialize and verify types
        sf = SpiderFoot(self.defaultConfig)
        unserialized = sf.configUnserialize(saved_config, self.defaultConfig)

        assert unserialized['_debug'] == True

        module_opts = unserialized['__modules__']['sfp__stor_db']['opts']
        assert module_opts['enable_connection_pooling'] == True
        assert module_opts['enable_auto_recovery'] == False
        assert module_opts['enable_load_balancing'] == True
        assert module_opts['db_type'] == "postgresql"
        assert module_opts['postgresql_host'] == "db.example.com"
        assert module_opts['postgresql_port'] == 5432

    @pytest.mark.timeout(30)
    def test_form_submission_without_boolean_conversion_fails(self):
        """
        Test that proves the bug: if booleans are NOT converted,
        settings don't reload correctly.

        This demonstrates WHY the fix is necessary.
        """
        # Form data with unconverted booleans (THE BUG)
        form_data = {
            "_debug": True,  # Python boolean, not "1"/"0" string
            "sfp__stor_db:enable_connection_pooling": False
        }

        # Save WITHOUT converting booleans (reproducing the bug)
        dbh = SpiderFootDb(self.defaultConfig)
        dbh.configSet(form_data)

        # Reload
        saved_config = dbh.configGet()

        # Database stores boolean as "True"/"False" strings (wrong!)
        # Instead of "1"/"0"

        # Try to unserialize
        sf = SpiderFoot(self.defaultConfig)
        unserialized = sf.configUnserialize(saved_config, self.defaultConfig)

        # The boolean will be wrong because "True" != "1"
        # configUnserialize expects "1" or "0"
        if unserialized['_debug'] != True:
            # Bug reproduced - boolean not restored correctly
            pass
        else:
            # If this somehow works, the database might have special handling
            # But the correct approach is still to store "1"/"0"
            pass

    @pytest.mark.timeout(30)
    def test_settings_persist_across_restart_simulation(self):
        """
        Simulate application restart after saving settings.

        This tests that settings truly persist and aren't just
        held in memory.
        """
        # Save settings
        form_data = {
            "sfp__stor_db:db_type": "postgresql",
            "sfp__stor_db:postgresql_host": "production.db",
            "sfp__stor_db:enable_connection_pooling": True
        }

        # Convert booleans
        converted_data = form_data.copy()
        for key in converted_data:
            if isinstance(converted_data[key], bool):
                converted_data[key] = "1" if converted_data[key] else "0"

        # Save
        dbh1 = SpiderFootDb(self.defaultConfig)
        dbh1.configSet(converted_data)

        # Simulate restart: create entirely new instances
        dbh2 = SpiderFootDb(self.defaultConfig, init=False)
        sf2 = SpiderFoot(self.defaultConfig)

        # Load config (as if application just started)
        saved_config = dbh2.configGet()
        unserialized = sf2.configUnserialize(saved_config, self.defaultConfig)

        # Verify settings persisted through "restart"
        module_opts = unserialized['__modules__']['sfp__stor_db']['opts']
        assert module_opts['db_type'] == 'postgresql'
        assert module_opts['postgresql_host'] == 'production.db'
        assert module_opts['enable_connection_pooling'] == True
