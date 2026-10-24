"""
Unit test conftest.py — Global database connection blocker.

This autouse fixture intercepts ALL psycopg2 connections for every unit test,
ensuring no test ever attempts a real database connection. The patch targets
the LOCAL import inside spiderfoot/db/db_core.py:754-755:

    import psycopg2.extras
    import psycopg2
    self.conn = psycopg2.connect(database_path)

By patching 'psycopg2' at the module level where it's imported, we block
all connection attempts globally.
"""

from typing import Generator

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_db_connection() -> Generator[MagicMock, None, None]:
    """Block all psycopg2 connections for every unit test.

    Provides a mock psycopg2 module that returns mock connections and cursors
    with sensible defaults (empty result sets, zero counts).

    Yields:
        MagicMock: The mocked psycopg2 module.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (0,)
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = None

    with patch('psycopg2.connect', return_value=mock_conn) as mock_connect, \
         patch('psycopg2.extras', create=True) as mock_extras:
        mock_extras.DictCursor = MagicMock()

        # Also patch at the db_core level to catch local imports
        with patch.dict('sys.modules', {
            'psycopg2': MagicMock(
                connect=mock_connect,
                extras=mock_extras,
                OperationalError=Exception,
                DatabaseError=Exception,
                InterfaceError=Exception,
                ProgrammingError=Exception,
            ),
            'psycopg2.extras': mock_extras,
        }):
            yield mock_connect
