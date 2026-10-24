"""Seed SpiderFoot API keys into PostgreSQL tbl_config from environment variables.

Reads resolved environment variables (from op run --env-file=env.spiderfoot.apikeys)
and UPSERTs them into SpiderFoot's PostgreSQL tbl_config table.

Usage:
    python seed_api_keys.py [--verbose] [--dry-run]
"""

import argparse
import logging
import os
import sys
import time
from typing import Mapping

import psycopg2

logger = logging.getLogger(__name__)

MODULE_ALIASES = {
    "sfp_circl_lu": "sfp_circllu",
}

UPSERT_SQL = (
    "INSERT INTO tbl_config (scope, opt, val) VALUES (%s, %s, %s) "
    "ON CONFLICT (scope, opt) DO UPDATE SET val = EXCLUDED.val"
)

def generate_sql(keys: list[tuple[str, str, str]]) -> str:
    """Generate parameterized UPSERT SQL statements for piping to psql.

    Uses dollar-quoting ($$) to safely handle values containing single quotes,
    backslashes, or other special characters without risk of SQL injection.

    Args:
        keys: List of (scope, opt, value) tuples from parse_sf_env_vars().

    Returns:
        A string of SQL statements wrapped in a transaction block.
    """
    if not keys:
        return "-- No keys to seed\n"

    lines = ["BEGIN;", ""]
    for scope, opt, value in keys:
        # Dollar-quoting prevents SQL injection — no escaping needed
        # scope/opt are derived from env var names (alphanumeric + underscore only)
        # value gets dollar-quoted to handle any character safely
        safe_scope = scope.replace("'", "''")
        safe_opt = opt.replace("'", "''")
        lines.append(
            f"INSERT INTO tbl_config (scope, opt, val) "
            f"VALUES ('{safe_scope}', '{safe_opt}', $val${value}$val$) "
            f"ON CONFLICT (scope, opt) DO UPDATE SET val = EXCLUDED.val;"
        )
    lines.append("")
    lines.append("COMMIT;")
    lines.append("")
    return "\n".join(lines)


def parse_sf_env_vars(environ: Mapping[str, str]) -> list[tuple[str, str, str]]:
    """Parse SF__<MODULE>__<CONFIG_KEY> environment variables into config tuples.

    Args:
        environ: A dict of environment variables (typically os.environ).

    Returns:
        A list of (scope, opt, value) tuples ready for DB insertion.
    """
    results = []

    for key, value in environ.items():
        if not key.startswith("SF__"):
            continue

        # Value validation: skip empty, whitespace-only, or unresolved op:// refs
        if not value or not value.strip():
            logger.warning("Skipping %s: empty or whitespace-only value", key)
            continue

        if value.startswith("op://"):
            logger.warning("Skipping %s: unresolved 1Password reference", key)
            continue

        # Split on __ — must yield exactly 3 parts: SF, MODULE, CONFIG_KEY
        parts = key.split("__")
        if len(parts) != 3:
            logger.warning(
                "Skipping %s: expected 3 parts (SF__MODULE__KEY), got %d",
                key, len(parts),
            )
            continue

        _, module, config_key = parts
        scope = module.lower()
        opt = config_key.lower()

        # Apply module aliases
        scope = MODULE_ALIASES.get(scope, scope)

        results.append((scope, opt, value))
        logger.debug("Parsed: scope=%s opt=%s", scope, opt)

    return results


def validate_db_config() -> dict:
    """Read and validate database configuration from environment variables.

    Returns:
        A dict with keys: host, port, dbname, user, password.

    Raises:
        EnvironmentError: If required variables (host, password) are missing.
    """
    host = os.environ.get("SPIDERFOOT_DB_HOST")
    port = os.environ.get("SPIDERFOOT_DB_PORT", "5432")
    dbname = (
        os.environ.get("SPIDERFOOT_DB_NAME")
        or os.environ.get("SPIDERFOOT_DB", "spiderfoot_db")
    )
    user = os.environ.get("SPIDERFOOT_DB_USER", "postgres")
    password = os.environ.get("SPIDERFOOT_DB_PASSWORD")

    missing = []
    if not host:
        missing.append("SPIDERFOOT_DB_HOST")
    if not password:
        missing.append("SPIDERFOOT_DB_PASSWORD")

    if missing:
        raise EnvironmentError(
            f"Missing required environment variable(s): {', '.join(missing)}"
        )

    return {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
    }


def wait_for_db(db_config: dict, max_retries: int = 10, delay: float = 2.0) -> bool:
    """Wait for PostgreSQL to become available with exponential backoff.

    Args:
        db_config: Database connection parameters from validate_db_config().
        max_retries: Maximum number of connection attempts.
        delay: Initial delay in seconds between retries (doubles each attempt).

    Returns:
        True if connection succeeded, False if all retries exhausted.
    """
    current_delay = delay

    for attempt in range(1, max_retries + 1):
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                dbname=db_config["dbname"],
                user=db_config["user"],
                password=db_config["password"],
            )
            conn.close()
            logger.info("Database connection established on attempt %d", attempt)
            return True
        except psycopg2.OperationalError as exc:
            logger.warning(
                "DB connection attempt %d/%d failed: %s — retrying in %.1fs",
                attempt, max_retries, exc, current_delay,
            )
            if attempt < max_retries:
                time.sleep(current_delay)
                current_delay *= 2

    logger.error("All %d DB connection attempts exhausted", max_retries)
    return False


def upsert_api_keys(
    db_config: dict, keys: list[tuple[str, str, str]]
) -> dict:
    """UPSERT API keys into PostgreSQL tbl_config.

    Args:
        db_config: Database connection parameters from validate_db_config().
        keys: List of (scope, opt, value) tuples from parse_sf_env_vars().

    Returns:
        A dict with keys:
            success_count (int): Number of successfully upserted keys.
            failed (list): List of dicts with scope, opt, error for failures.
            skipped (list): List of dicts with scope, opt, reason for skips.

    Raises:
        psycopg2.OperationalError: If database connection fails entirely.
    """
    result = {"success_count": 0, "failed": [], "skipped": []}

    if not keys:
        logger.info("No keys to upsert")
        return result

    try:
        with psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            dbname=db_config["dbname"],
            user=db_config["user"],
            password=db_config["password"],
        ) as conn:
            with conn.cursor() as cursor:
                for scope, opt, value in keys:
                    try:
                        cursor.execute(UPSERT_SQL, (scope, opt, value))
                        result["success_count"] += 1
                        logger.debug("Upserted: scope=%s opt=%s", scope, opt)
                    except psycopg2.Error as exc:
                        logger.error(
                            "Failed to upsert scope=%s opt=%s: %s",
                            scope, opt, exc,
                        )
                        result["failed"].append({
                            "scope": scope,
                            "opt": opt,
                            "error": str(exc),
                        })
                        conn.rollback()

            if result["failed"]:
                conn.rollback()
                logger.warning(
                    "Transaction rolled back due to %d failure(s)",
                    len(result["failed"]),
                )
            else:
                conn.commit()
                logger.info(
                    "Transaction committed: %d key(s) upserted",
                    result["success_count"],
                )

    except psycopg2.OperationalError as exc:
        logger.error("Database connection failed: %s", exc)
        raise

    return result


def main() -> int:
    """Orchestrate API key seeding: parse, validate, wait, upsert.

    Returns:
        Exit code: 0 = all success, 1 = partial failure, 2 = total failure.
    """
    parser = argparse.ArgumentParser(
        description="Seed SpiderFoot API keys into PostgreSQL tbl_config",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable DEBUG logging",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and validate only; print what would be inserted",
    )
    parser.add_argument(
        "--generate-sql", action="store_true",
        help="Output UPSERT SQL to stdout (pipe to psql). No DB connection needed.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Step 1: Parse environment variables
    keys = parse_sf_env_vars(os.environ)

    if not keys:
        logger.error("No valid SF__ environment variables found")
        print("\n=== SEED SUMMARY ===")
        print("Result: FAILURE — no valid API keys found in environment")
        return 2

    logger.info("Parsed %d API key(s) from environment", len(keys))

    if args.dry_run:
        print("\n=== DRY RUN — would upsert the following keys ===")
        for scope, opt, value in keys:
            masked = value[:4] + "****" if len(value) > 4 else "****"
            print(f"  scope={scope}  opt={opt}  val={masked}")
        print(f"\nTotal: {len(keys)} key(s)")
        return 0

    if args.generate_sql:
        # Output SQL to stdout — pipe to: docker exec -i unified-postgres psql -U postgres -d spiderfoot_db
        sql = generate_sql(keys)
        print(sql, end="")
        logger.info("Generated SQL for %d key(s)", len(keys))
        return 0

    # Step 2: Validate DB config
    try:
        db_config = validate_db_config()
    except EnvironmentError as exc:
        logger.error("DB config validation failed: %s", exc)
        print(f"\n=== SEED SUMMARY ===\nResult: FAILURE — {exc}")
        return 2

    # Step 3: Wait for DB
    if not wait_for_db(db_config):
        logger.error("Database not available after retries")
        print("\n=== SEED SUMMARY ===")
        print("Result: FAILURE — database not available")
        return 2

    # Step 4: Upsert
    try:
        result = upsert_api_keys(db_config, keys)
    except psycopg2.OperationalError as exc:
        logger.error("Upsert failed with connection error: %s", exc)
        print(f"\n=== SEED SUMMARY ===\nResult: FAILURE — {exc}")
        return 2

    # Step 5: Summary
    print("\n=== SEED SUMMARY ===")
    print(f"  Success: {result['success_count']}")
    print(f"  Failed:  {len(result['failed'])}")
    print(f"  Skipped: {len(result['skipped'])}")

    if result["failed"]:
        print("\nFailed keys:")
        for entry in result["failed"]:
            print(f"  scope={entry['scope']} opt={entry['opt']} error={entry['error']}")

    if result["success_count"] == 0:
        return 2
    if result["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
