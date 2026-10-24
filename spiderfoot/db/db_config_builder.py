"""
Centralized database configuration builder for SpiderFoot.

This module provides a single source of truth for PostgreSQL database configuration,
ensuring consistent connection string format across all entry points (CLI, WebUI, API).

Usage:
    from spiderfoot.db.db_config_builder import build_database_config

    config = build_database_config()
    # Returns: {'__database': 'postgresql://...', '__dbtype': 'postgresql'}
"""

import os
from typing import Dict
from urllib.parse import quote_plus


def build_database_config() -> Dict[str, str]:
    """
    Build database configuration from environment variables.

    Reads PostgreSQL connection parameters from environment variables and
    constructs a standardized DSN URI connection string.

    Environment Variables (in order of preference):
        SPIDERFOOT_DB_TYPE: Database type (default: 'postgresql', must be 'postgresql')
        SPIDERFOOT_DB_HOST: PostgreSQL hostname (default: 'localhost')
        SPIDERFOOT_DB_PORT: PostgreSQL port (default: '5432')
        SPIDERFOOT_DB_NAME or SPIDERFOOT_DB: Database name (REQUIRED)
        SPIDERFOOT_DB_USER: Database username (default: 'spiderfoot')
        SPIDERFOOT_DB_PASSWORD or SPIDERFOOT_DB_PASS: Database password (optional)

    Returns:
        Dict with '__database' (DSN URI) and '__dbtype' ('postgresql')

    Raises:
        ValueError: If database type is not PostgreSQL or required parameters are missing

    Examples:
        >>> os.environ['SPIDERFOOT_DB_NAME'] = 'mydb'
        >>> config = build_database_config()
        >>> config['__database']
        'postgresql://spiderfoot@localhost:5432/mydb'

        >>> os.environ['SPIDERFOOT_DB_PASSWORD'] = 'p@ss:word'
        >>> config = build_database_config()
        >>> config['__database']
        'postgresql://spiderfoot:p%40ss%3Aword@localhost:5432/mydb'
    """
    # Read database type (enforce PostgreSQL only)
    db_type = os.getenv('SPIDERFOOT_DB_TYPE', 'postgresql').lower()

    if db_type != 'postgresql':
        raise ValueError(
            f"Database type '{db_type}' is not supported. "
            "SpiderFoot requires PostgreSQL. Set SPIDERFOOT_DB_TYPE=postgresql"
        )

    # Read connection parameters from environment variables
    # Support both new (_NAME, _PASSWORD) and legacy (_DB, _PASS) variable names
    db_host = os.getenv('SPIDERFOOT_DB_HOST', 'localhost')
    db_port = os.getenv('SPIDERFOOT_DB_PORT', '5432')

    # Prefer SPIDERFOOT_DB_NAME, fall back to SPIDERFOOT_DB for backward compatibility
    db_name = os.getenv('SPIDERFOOT_DB_NAME') or os.getenv('SPIDERFOOT_DB', '')

    db_user = os.getenv('SPIDERFOOT_DB_USER', 'spiderfoot')

    # Prefer SPIDERFOOT_DB_PASSWORD, fall back to SPIDERFOOT_DB_PASS for backward compatibility
    db_pass = os.getenv('SPIDERFOOT_DB_PASSWORD') or os.getenv('SPIDERFOOT_DB_PASS', '')

    # Validate required parameters
    if not db_name:
        raise ValueError(
            "Database name is required. Set one of these environment variables:\n"
            "  SPIDERFOOT_DB_NAME=your_database (recommended)\n"
            "  SPIDERFOOT_DB=your_database (legacy)\n"
            "\n"
            "Example:\n"
            "  export SPIDERFOOT_DB_NAME=spiderfoot_db"
        )

    # Construct PostgreSQL DSN URI
    # Format: postgresql://user:password@host:port/database
    # URL-encode password to handle special characters (@, :, /, etc.)
    if db_pass:
        # URL-encode password for safe inclusion in URI
        encoded_pass = quote_plus(db_pass)
        dsn = f"postgresql://{db_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}"
    else:
        # No password - construct URI without password component
        dsn = f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"

    return {
        '__database': dsn,
        '__dbtype': 'postgresql'
    }


def get_database_string() -> str:
    """
    Get database connection string (DSN URI format).

    Convenience function that returns just the connection string without
    the full configuration dictionary.

    Returns:
        PostgreSQL DSN URI string

    Raises:
        ValueError: If database configuration is invalid

    Example:
        >>> dsn = get_database_string()
        >>> dsn
        'postgresql://spiderfoot@localhost:5432/mydb'
    """
    config = build_database_config()
    return config['__database']


def validate_database_config() -> bool:
    """
    Validate database configuration without raising exceptions.

    Useful for health checks and startup validation.

    Returns:
        True if configuration is valid, False otherwise

    Example:
        >>> if validate_database_config():
        ...     print("Database configuration is valid")
        ... else:
        ...     print("Database configuration is missing or invalid")
    """
    try:
        build_database_config()
        return True
    except (ValueError, KeyError):
        return False


def get_config_help() -> str:
    """
    Get help text for database configuration.

    Returns detailed information about environment variables and setup.

    Returns:
        Multi-line help text string
    """
    return """PostgreSQL Database Configuration for SpiderFoot

Required Environment Variables:
  SPIDERFOOT_DB_NAME or SPIDERFOOT_DB    Database name (REQUIRED)

Optional Environment Variables:
  SPIDERFOOT_DB_TYPE=postgresql          Database type (default: postgresql)
  SPIDERFOOT_DB_HOST=localhost           PostgreSQL hostname (default: localhost)
  SPIDERFOOT_DB_PORT=5432               PostgreSQL port (default: 5432)
  SPIDERFOOT_DB_USER=spiderfoot         Database username (default: spiderfoot)
  SPIDERFOOT_DB_PASSWORD                Database password (recommended)

  Legacy variable names (backward compatibility):
  SPIDERFOOT_DB                         Same as SPIDERFOOT_DB_NAME
  SPIDERFOOT_DB_PASS                    Same as SPIDERFOOT_DB_PASSWORD

Example Configuration:
  export SPIDERFOOT_DB_TYPE=postgresql
  export SPIDERFOOT_DB_HOST=localhost
  export SPIDERFOOT_DB_PORT=5432
  export SPIDERFOOT_DB_NAME=spiderfoot_db
  export SPIDERFOOT_DB_USER=spiderfoot
  export SPIDERFOOT_DB_PASSWORD=your_secure_password

Docker Configuration:
  environment:
    - SPIDERFOOT_DB_TYPE=postgresql
    - SPIDERFOOT_DB_HOST=postgres
    - SPIDERFOOT_DB_NAME=spiderfoot_db
    - SPIDERFOOT_DB_USER=spiderfoot
    - SPIDERFOOT_DB_PASSWORD=your_secure_password

For more information, see docs/POSTGRESQL_SETUP.md
"""
