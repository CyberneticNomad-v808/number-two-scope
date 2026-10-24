#!/bin/bash
# =============================================================================
# seed-api-keys.sh — Resolve 1Password secrets and seed into SpiderFoot DB
# =============================================================================
#
# Runs from the HOST. Uses `op run` to resolve op:// secret references in
# env.spiderfoot.apikeys, generates SQL via seed_api_keys.py --generate-sql,
# and pipes it into PostgreSQL via docker exec.
#
# Usage:
#   ./seed-api-keys.sh                # Full seed into DB
#   ./seed-api-keys.sh --dry-run      # Preview only, no DB writes
#   ./seed-api-keys.sh --verbose      # Debug logging
#
# Prerequisites:
#   - 1Password CLI authenticated (op signin)
#   - unified-postgres container running
#   - env.spiderfoot.apikeys file present
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/env.spiderfoot.apikeys"
SEED_SCRIPT="${SCRIPT_DIR}/seed_api_keys.py"
DB_CONTAINER="unified-postgres"
DB_NAME="spiderfoot_db"
DB_USER="postgres"

# Validate required files exist
if [ ! -f "${ENV_FILE}" ]; then
    echo "ERROR: env.spiderfoot.apikeys not found at ${ENV_FILE}"
    exit 2
fi

if [ ! -f "${SEED_SCRIPT}" ]; then
    echo "ERROR: seed_api_keys.py not found at ${SEED_SCRIPT}"
    exit 2
fi

# Check that the postgres container is running
if ! docker inspect -f '{{.State.Running}}' "${DB_CONTAINER}" 2>&1 | grep -q "true"; then
    echo "ERROR: Container '${DB_CONTAINER}' is not running."
    echo "       Start it with: docker compose up -d unified-postgres"
    exit 2
fi

echo "=== SpiderFoot API Key Seeder ==="
echo "Resolving secrets via 1Password CLI..."
echo ""

# Handle --dry-run: resolve secrets, show what would be inserted, no DB touch
if [[ "${1:-}" == "--dry-run" ]]; then
    op run --env-file="${ENV_FILE}" -- python3 "${SEED_SCRIPT}" --dry-run
    exit $?
fi

# Handle --verbose flag for generate-sql
VERBOSE_FLAG=""
if [[ "${1:-}" == "--verbose" ]]; then
    VERBOSE_FLAG="--verbose"
fi

# Full seed: resolve secrets → generate SQL → pipe to psql via docker exec
op run --env-file="${ENV_FILE}" -- python3 "${SEED_SCRIPT}" --generate-sql ${VERBOSE_FLAG} \
    | docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1

EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=== Seeding complete ==="
else
    echo ""
    echo "=== Seeding FAILED (exit code ${EXIT_CODE}) ==="
fi

exit $EXIT_CODE
