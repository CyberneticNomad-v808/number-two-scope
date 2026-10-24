"""Unit tests for seed_api_keys.py — SpiderFoot API key database seeder.

Tests are organized by function:
- parse_sf_env_vars
- validate_db_config
- upsert_api_keys (mocked psycopg2)
- main (integration-style with mocks)
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on sys.path so we can import seed_api_keys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import seed_api_keys


# =============================================================================
# parse_sf_env_vars
# =============================================================================

class TestParseSfEnvVars:
    """Tests for parse_sf_env_vars(environ) -> list[tuple[str, str, str]]."""

    def test_parse_valid_env_vars(self):
        """Standard SF__ vars produce correct (scope, opt, val) tuples."""
        environ = {
            "SF__SFP_VIRUSTOTAL__API_KEY": "abc123",
            "SF__SFP_SHODAN__API_KEY": "def456",
        }
        result = seed_api_keys.parse_sf_env_vars(environ)
        assert ("sfp_virustotal", "api_key", "abc123") in result
        assert ("sfp_shodan", "api_key", "def456") in result
        assert len(result) == 2

    def test_parse_skips_empty_values(self):
        """Empty string values are skipped."""
        environ = {
            "SF__SFP_VIRUSTOTAL__API_KEY": "",
            "SF__SFP_SHODAN__API_KEY": "   ",
        }
        result = seed_api_keys.parse_sf_env_vars(environ)
        assert len(result) == 0

    def test_parse_skips_unresolved_op_refs(self):
        """Values starting with 'op://' (unresolved 1Password refs) are skipped."""
        environ = {
            "SF__SFP_VIRUSTOTAL__API_KEY": "op://LOCAL_DEV_VAULT/OSINT Free API Keys/foo",
            "SF__SFP_SHODAN__API_KEY": "real_key_value",
        }
        result = seed_api_keys.parse_sf_env_vars(environ)
        assert len(result) == 1
        assert result[0] == ("sfp_shodan", "api_key", "real_key_value")

    def test_parse_skips_non_sf_vars(self):
        """PATH, HOME, and other non-SF__ vars are ignored."""
        environ = {
            "PATH": "/usr/bin",
            "HOME": "/home/user",
            "SPIDERFOOT_DB_HOST": "localhost",
            "SF__SFP_SHODAN__API_KEY": "mykey",
        }
        result = seed_api_keys.parse_sf_env_vars(environ)
        assert len(result) == 1
        assert result[0][0] == "sfp_shodan"

    def test_parse_applies_module_aliases(self):
        """sfp_circl_lu is aliased to sfp_circllu."""
        environ = {
            "SF__SFP_CIRCL_LU__API_KEY": "circl_key_123",
        }
        result = seed_api_keys.parse_sf_env_vars(environ)
        assert len(result) == 1
        assert result[0] == ("sfp_circllu", "api_key", "circl_key_123")

    def test_parse_rejects_malformed_keys_too_few_parts(self):
        """SF__ONLY_ONE_PART has fewer than 3 parts and is skipped."""
        environ = {
            "SF__ONLY_ONE_PART": "somevalue",
        }
        result = seed_api_keys.parse_sf_env_vars(environ)
        assert len(result) == 0

    def test_parse_rejects_malformed_keys_too_many_parts(self):
        """SF__TOO__MANY__PARTS has more than 3 parts and is skipped."""
        environ = {
            "SF__TOO__MANY__PARTS": "somevalue",
        }
        result = seed_api_keys.parse_sf_env_vars(environ)
        assert len(result) == 0


# =============================================================================
# validate_db_config
# =============================================================================

class TestValidateDbConfig:
    """Tests for validate_db_config() -> dict."""

    def test_validate_all_vars_present(self):
        """Returns correct dict when all vars are set."""
        env = {
            "SPIDERFOOT_DB_HOST": "db.example.com",
            "SPIDERFOOT_DB_PORT": "5433",
            "SPIDERFOOT_DB_NAME": "mydb",
            "SPIDERFOOT_DB_USER": "admin",
            "SPIDERFOOT_DB_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env, clear=True):
            result = seed_api_keys.validate_db_config()
        assert result == {
            "host": "db.example.com",
            "port": "5433",
            "dbname": "mydb",
            "user": "admin",
            "password": "secret",
        }

    def test_validate_missing_host_raises(self):
        """EnvironmentError raised when SPIDERFOOT_DB_HOST is missing."""
        env = {
            "SPIDERFOOT_DB_PORT": "5432",
            "SPIDERFOOT_DB_NAME": "spiderfoot_db",
            "SPIDERFOOT_DB_USER": "postgres",
            "SPIDERFOOT_DB_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(EnvironmentError):
                seed_api_keys.validate_db_config()

    def test_validate_missing_password_raises(self):
        """EnvironmentError raised when SPIDERFOOT_DB_PASSWORD is missing."""
        env = {
            "SPIDERFOOT_DB_HOST": "localhost",
            "SPIDERFOOT_DB_PORT": "5432",
            "SPIDERFOOT_DB_NAME": "spiderfoot_db",
            "SPIDERFOOT_DB_USER": "postgres",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(EnvironmentError):
                seed_api_keys.validate_db_config()

    def test_validate_defaults(self):
        """Port defaults to 5432, dbname defaults to spiderfoot_db."""
        env = {
            "SPIDERFOOT_DB_HOST": "localhost",
            "SPIDERFOOT_DB_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env, clear=True):
            result = seed_api_keys.validate_db_config()
        assert result["port"] == "5432"
        assert result["dbname"] == "spiderfoot_db"
        assert result["user"] == "postgres"


# =============================================================================
# generate_sql
# =============================================================================

class TestGenerateSql:
    """Tests for generate_sql(keys) -> str."""

    def test_generate_sql_produces_valid_upserts(self):
        """Generated SQL contains BEGIN, COMMIT, and correct UPSERT statements."""
        keys = [
            ("sfp_shodan", "api_key", "abc123"),
            ("sfp_virustotal", "api_key", "def456"),
        ]
        sql = seed_api_keys.generate_sql(keys)
        assert "BEGIN;" in sql
        assert "COMMIT;" in sql
        assert "sfp_shodan" in sql
        assert "sfp_virustotal" in sql
        assert "abc123" in sql
        assert "def456" in sql
        assert sql.count("INSERT INTO tbl_config") == 2

    def test_generate_sql_empty_keys(self):
        """Empty key list returns a comment, no SQL statements."""
        sql = seed_api_keys.generate_sql([])
        assert "No keys to seed" in sql
        assert "INSERT" not in sql

    def test_generate_sql_dollar_quoting_prevents_injection(self):
        """Values with single quotes are safely dollar-quoted."""
        keys = [("sfp_test", "api_key", "it's a key with 'quotes'")]
        sql = seed_api_keys.generate_sql(keys)
        # Dollar-quoting wraps the value — no bare single quotes in the value
        assert "$val$it's a key with 'quotes'$val$" in sql
        assert "BEGIN;" in sql
        assert "COMMIT;" in sql

    def test_generate_sql_transaction_wrapping(self):
        """SQL is wrapped in BEGIN/COMMIT for atomicity."""
        keys = [("sfp_shodan", "api_key", "key1")]
        sql = seed_api_keys.generate_sql(keys)
        lines = sql.strip().split("\n")
        assert lines[0] == "BEGIN;"
        assert lines[-1] == "COMMIT;"


# =============================================================================
# upsert_api_keys (mock psycopg2)
# =============================================================================

class TestUpsertApiKeys:
    """Tests for upsert_api_keys(db_config, keys) -> dict."""

    def test_upsert_success(self):
        """All keys inserted, returns correct success count."""
        db_config = {
            "host": "localhost", "port": "5432",
            "dbname": "spiderfoot_db", "user": "postgres", "password": "secret",
        }
        keys = [
            ("sfp_shodan", "api_key", "key1"),
            ("sfp_virustotal", "api_key", "key2"),
        ]
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("seed_api_keys.psycopg2") as mock_psycopg2:
            mock_psycopg2.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_psycopg2.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_psycopg2.OperationalError = Exception

            result = seed_api_keys.upsert_api_keys(db_config, keys)

        assert result["success_count"] == 2
        assert result["failed"] == []

    def test_upsert_empty_list(self):
        """No keys provided, returns 0 success count without DB call."""
        db_config = {
            "host": "localhost", "port": "5432",
            "dbname": "spiderfoot_db", "user": "postgres", "password": "secret",
        }
        result = seed_api_keys.upsert_api_keys(db_config, [])
        assert result["success_count"] == 0
        assert result["failed"] == []
        assert result["skipped"] == []

    def test_upsert_db_error_rolls_back(self):
        """Simulate DB error during execute, verify rollback is called."""
        db_config = {
            "host": "localhost", "port": "5432",
            "dbname": "spiderfoot_db", "user": "postgres", "password": "secret",
        }
        keys = [("sfp_shodan", "api_key", "key1")]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("seed_api_keys.psycopg2") as mock_psycopg2:
            mock_psycopg2.Error = type("Error", (Exception,), {})
            mock_cursor.execute.side_effect = mock_psycopg2.Error("DB write error")
            mock_psycopg2.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_psycopg2.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_psycopg2.OperationalError = Exception

            result = seed_api_keys.upsert_api_keys(db_config, keys)

        assert result["success_count"] == 0
        assert len(result["failed"]) == 1
        assert result["failed"][0]["scope"] == "sfp_shodan"
        mock_conn.rollback.assert_called()


# =============================================================================
# main (integration-style with mocks)
# =============================================================================

class TestMain:
    """Tests for main() -> int."""

    def test_main_dry_run(self):
        """In dry-run mode, no DB calls are made."""
        env = {
            "SF__SFP_SHODAN__API_KEY": "mykey",
            "SPIDERFOOT_DB_HOST": "localhost",
            "SPIDERFOOT_DB_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env, clear=False), \
             patch("sys.argv", ["seed_api_keys.py", "--dry-run"]), \
             patch("seed_api_keys.upsert_api_keys") as mock_upsert, \
             patch("seed_api_keys.wait_for_db") as mock_wait:
            exit_code = seed_api_keys.main()

        mock_upsert.assert_not_called()
        mock_wait.assert_not_called()
        assert exit_code == 0

    def test_main_returns_0_on_success(self):
        """Returns 0 when all keys are upserted successfully."""
        env = {
            "SF__SFP_SHODAN__API_KEY": "mykey",
            "SPIDERFOOT_DB_HOST": "localhost",
            "SPIDERFOOT_DB_PASSWORD": "secret",
        }
        upsert_result = {"success_count": 1, "failed": [], "skipped": []}
        with patch.dict(os.environ, env, clear=False), \
             patch("sys.argv", ["seed_api_keys.py"]), \
             patch("seed_api_keys.wait_for_db", return_value=True), \
             patch("seed_api_keys.upsert_api_keys", return_value=upsert_result):
            exit_code = seed_api_keys.main()

        assert exit_code == 0

    def test_main_returns_2_on_no_keys(self):
        """Returns 2 when no valid SF__ keys are found."""
        env = {
            "SPIDERFOOT_DB_HOST": "localhost",
            "SPIDERFOOT_DB_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env, clear=True), \
             patch("sys.argv", ["seed_api_keys.py"]):
            exit_code = seed_api_keys.main()

        assert exit_code == 2
