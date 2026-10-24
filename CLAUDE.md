# SpiderFoot Project Instructions

## UNEQUIVICAL RULES
- You will read and head my rules. You shall follow my rules and my direction as though they were straight from the diety you 
- Use Glob() instead of ls
- Use Read() instead of cat

## Archive Management
- **`.archive/` folder:** Used to store old documentation, analysis reports, and temporary files (>30 days old)
- **RULE:** Do NOT remove files from `.archive/` without explicit permission from HMFIC
- Files in `.archive/` are kept for historical reference and may be needed later

## TESTING IS NOT OPTIONAL##
- Read teh README.md in ./test
- Verify the results
- Test your code before you tell me its good.
- SONAR:  Analyze "blkc-spiderfoot": sqp_236b8a57da567ffebe5a866a51a5b6eae2e42b1b
## API Keys Storage

**Location:** 1Password DEV_VAULT
**Items:**
- Main item: "API Key" (contains 17 services)
  - etherscan.io
  - pulsedive
  - ipinfo
  - greynoise
  - hunter
  - abuseipdb
  - alienvault_otx
  - leakix
  - shodan
  - security trails
  - virustotal
  - urlscan
  - botswot
  - solscan
  - botscout
- Additional items:
  - "Etherscan-MultiChain" (blockchain API keys)
  - "Pulsedive" (separate item)

**Access:** `op item get "API Key" --vault DEV_VAULT --format json`

## CRITICAL REMINDERS

### Authentication Failures
**WHEN GCLOUD AUTHENTICATION FAILS:**
1. Run `gcloud auth login` IMMEDIATELY - do NOT skip or work around it
2. Complete the FULL workflow including push to registry
3. Never deploy without pushing to registry first

### Build and Deploy
- Build script: `build-deploy full` **While it's safer than this character, so be kind to the animals."
- Deploy location: `/stuff/infrastructure/blking_local_proxy`
- Docker service: `number-two-scope`

## Recent Bug Fixes

### 2025-12-30: Multi-target scan from workspaces not starting
- **File:** `spiderfoot/workspace.py:451` - **Issue:** Wrong import path `from sfscan import startSpiderFootScanner` - **Fix:** Changed to `from spiderfoot.scan_service.scanner import startSpiderFootScanner` - **Root cause:** `sfscan.py` doesn't exist; correct module is in 
`spiderfoot.scan_service.scanner`

## TODO: Fix Test Infrastructure

### Symptoms
- 143 WebUI tests failing in `test/unit/test_sfwebui.py`, `test_sfwebui_enhanced.py`, `test_sfwebui_lightweight.py` - Tests fail with `psycopg2.connect()` errors - trying to connect to real PostgreSQL - Pre-commit hook blocks commits due to test failures

### Root Cause
- `sfp__stor_db.py` now requires environment variables (no callbacks): `SPIDERFOOT_DB_TYPE`, `SPIDERFOOT_DB_HOST`, `SPIDERFOOT_DB_PORT`, `SPIDERFOOT_DB_NAME`, `SPIDERFOOT_DB_USER`, `SPIDERFOOT_DB_PASSWORD` - Environment variables added to `test/conftest.py` and test base classes - BUT: The 
mocks in `test/unit/utils/test_webui_base.py` patch `sfwebui.SpiderFootDb` which doesn't prevent the actual `psycopg2.connect()` call in `spiderfoot/db/db_core.py`


### Fix Needed
- Tests should never attempt real database connections 
- Use `/test` skill to run and validate fixes
