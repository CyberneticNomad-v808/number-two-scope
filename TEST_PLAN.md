# SpiderFoot Test Plan

**Last Updated:** 2026-02-06
**Maintainer:** BL King Consulting

---

## 1. Current State (As-Is)

| Component | Status | Location |
|-----------|--------|----------|
| Test directory (~578 files) | Active | `test/` |
| Modules directory (~230 files) | Active | `modules/` |
| As-is documentation suite (~123,000 words) | Active | `spiderfoot-as-is-documentation/` |
| `setup.cfg` (flake8/darglint config) | Active | project root |
| `sonar-project.properties` | Active | project root |
| `.coveragerc` | Active | project root |
| `.pylintrc` | Active | project root |
| Source code (`spiderfoot/`) | Active | project root |
| Correlation rules (`correlations/`) | Active | 54 YAML files |

### Known Blocker

143 WebUI tests are currently failing. Root cause:

- `sfp__stor_db.py` now requires environment variables (`SPIDERFOOT_DB_TYPE`, `SPIDERFOOT_DB_HOST`, `SPIDERFOOT_DB_PORT`, `SPIDERFOOT_DB_NAME`, `SPIDERFOOT_DB_USER`, `SPIDERFOOT_DB_PASSWORD`) with no callback fallback.
- Environment variables are set in `test/conftest.py` and test base classes.
- **But:** Mocks in `test/unit/utils/test_webui_base.py` patch `sfwebui.SpiderFootDb`, which does **not** prevent the actual `psycopg2.connect()` call in `spiderfoot/db/db_core.py`.
- Tests should never attempt real database connections.

---

## 2. Test Infrastructure Inventory

### 2.1 Test File Counts

| Category | File Count | Location |
|----------|------------|----------|
| Unit tests | ~318 | `test/unit/` |
| Integration tests | ~242 | `test/integration/` |
| Regression tests | 3 | `test/regression/` |
| Acceptance tests (Robot) | 4 | `test/acceptance/` |
| Mock modules | 4 | `test/mocks/` |
| Fixture modules | 4 | `test/fixtures/` |
| Utility modules | 3+ | `test/unit/utils/` |
| **Total** | **~578** | |

### 2.2 Test Suites

**Unit Tests** (`test/unit/`)
- `test/unit/modules/` — Per-module unit tests for every `sfp_*.py` module
- `test/unit/spiderfoot/` — Core engine tests (correlation engine performance, unit tests, helpers, workspace)
- `test/unit/utils/` — Utility tests (helpers, decorators, resources, common, timeout)

**Integration Tests** (`test/integration/`)
- `test/integration/modules/` — Module tests against real/mocked external data sources
- `test/integration/spiderfoot/` — Core integration (correlation engine)
- `test/integration/test_sf.py`, `test_sfcli.py`, `test_sfwebui.py` — Application-level integration

**Regression Tests** (`test/regression/`)
- `test_database_settings_persistence.py` — DB settings persistence bug (27 tests, 5 classes)
- `test_correlation_schema_validation.py` — Correlation schema validation
- `test_webui_settings_form_submission.py` — WebUI settings form submission

**Acceptance Tests** (`test/acceptance/`)
- `scan-firefox.robot` — Firefox headless browser tests
- `scan-chrome.robot` — Chrome headless browser tests
- `settings_persistence.robot` — Settings persistence E2E
- `variables.robot` — Shared Robot Framework variables

### 2.3 Test Support Infrastructure

**conftest.py** (276 lines) provides:
- Module-level `psycopg2.connect` mock (patched before any imports)
- `psycopg2.extras.DictCursor` mock
- Environment variable setup for PostgreSQL test config
- `SafeHandler` / `SafeFileHandler` — Logging handlers that suppress BrokenPipeError during xdist termination
- `check_resource_leaks` fixture — Thread leak detection (autouse)
- `default_options` fixture — Module, WebUI, and CLI default settings
- `session_cleanup` fixture — Garbage collection, thread cleanup, logging shutdown
- 30-minute global timeout (daemon thread)
- Thread tracking per test

**Mocks** (`test/mocks/`):
- `mock_database.py` — Database mocking utilities
- `mock_filesystem.py` — File system mocking
- `mock_modules.py` — SpiderFoot module mocking
- `mock_network.py` — Network/HTTP mocking

**Fixtures** (`test/fixtures/`):
- `database_fixtures.py` — Database test data and connections
- `event_fixtures.py` — SpiderFoot event test data
- `filesystem_fixtures.py` — File system test scenarios
- `network_fixtures.py` — HTTP/network response fixtures

### 2.4 Test Runners

**`test/run`** (560 lines) — Interactive menu-driven runner:
- 8 menu options for different test configurations
- Database configuration dialog with validation
- Color-coded output
- Test type selectors (unit, standard, all, module-only)
- Was being rebuilt using BLKC universal-script-template (incomplete — see `test/TODO.md`)

**`test/run_simple`** (94 lines) — Minimal CI/CD runner:
- Environment validation
- Direct pytest execution
- Minimal error handling

---

## 3. Test Dependencies

### 3.1 Core Test Dependencies (from `test/requirements.txt`)

```
-r ../requirements.txt          # Inherits project dependencies
pytest==8.4.1                   # Test framework
pytest-cov==6.2.1               # Coverage reporting
pytest-mock==3.14.1             # Mocking fixtures
pytest-xdist==3.8.0             # Parallel/distributed execution
responses==0.25.7               # HTTP response mocking
flask                           # Web framework for test servers
telethon                        # Telegram API testing
openai                          # AI API testing
```

### 3.2 Linting Dependencies (from `test/requirements.txt`)

```
flake8==7.3.0                   # Core linter
flake8-annotations==3.1.1       # Type annotation checks
flake8-blind-except==0.2.1      # Bare except detection
flake8-bugbear==24.12.12        # Additional bug detection
flake8-builtins==2.5.0          # Builtin shadowing
flake8-quotes==3.4.0            # Quote consistency
flake8-return==1.2.0            # Return statement checks
flake8-sfs==1.0.0               # SpiderFoot-specific rules
flake8-simplify==0.22.0         # Code simplification suggestions
darglint==1.8.1                 # Docstring validation
dlint==0.16.0                   # Security linting
pycodestyle==2.14.0             # Style checking
```

### 3.3 Acceptance Test Dependencies (from `test/acceptance/requirements.txt`)

```
-r ../requirements.txt          # Inherits project dependencies
robotframework                  # Test automation framework
robotframework-seleniumlibrary  # Browser automation
chromedriver                    # Chrome/Chromium driver
```

### 3.4 Environment Variables Required

```bash
SPIDERFOOT_DB_TYPE=postgresql
SPIDERFOOT_DB_HOST=localhost
SPIDERFOOT_DB_PORT=5432
SPIDERFOOT_DB_NAME=spiderfoot_test
SPIDERFOOT_DB_USER=spiderfoot
SPIDERFOOT_DB_PASSWORD=
```

---

## 4. Documented Test Results

### 4.1 Regression Suite: Database Settings Persistence

**Source:** `REGRESSION_TEST_SUMMARY.md`, `REGRESSION_TEST_ANALYSIS_REPORT.md`

**Bug:** Module settings (sfp__stor_db PostgreSQL connection settings) were not persisting when saved through the WebUI settings page.

**Root Cause:** In `spiderfoot/webui/routes.py`, modules were loaded AFTER attempting to unserialize config from the database. No reference point for module settings existed.

**Fix:** Moved module loading to happen BEFORE database config unserialization in `WebUiRoutes.__init__`.

**Test Coverage (Enhanced Suite):**

| Class | Tests | Purpose |
|-------|-------|---------|
| `TestDatabaseSettingsPersistence` | 7 | Core persistence (save, unserialize, restart durability, partial update, roundtrip) |
| `TestBooleanSettingsPersistence` | 1 | Boolean type handling |
| `TestBugVerification` | 3 | Bug reproduction and fix validation |
| `TestErrorConditions` | 7 | Invalid types, empty/null values, malformed names, special characters (6 parameterized), long values |
| `TestIntegration` | 3 | Full save/load cycle, multi-module coordination, WebUI routes startup |
| **Total** | **21** | (27 with parameterized expansion) |

**Critical Tests:**
- `TestBugVerification::test_original_bug_modules_not_loaded_first` — Must fail if bug reintroduced
- `TestBugVerification::test_modules_loaded_before_database_config_restored` — Verifies loading order with mocks

**Coverage Matrix:**

| Feature | Unit | Integration | Error Handling | Edge Cases |
|---------|------|-------------|----------------|------------|
| Save settings | Yes | Yes | Partial | Yes |
| Load settings | Yes | Yes | Yes | Yes |
| Module loading | Yes | Yes | N/A | Yes |
| Type conversion | Yes | Yes | Yes | Yes |
| Boolean handling | Yes | Yes | N/A | Yes |
| Special characters | Yes | Yes | N/A | Yes |
| WebUI routes | Yes | Yes | N/A | Yes |
| Bug reproduction | Yes | Yes | N/A | Yes |

**Initial Analysis Rating:** 6.5/10 (before enhancement)
**Post-Enhancement Rating:** Production-ready (21 test methods, 163% increase)

### 4.2 Known Test Failures

**143 WebUI tests** in `test/unit/test_sfwebui.py`, `test_sfwebui_enhanced.py`, `test_sfwebui_lightweight.py`:
- Fail with `psycopg2.connect()` errors — attempting real PostgreSQL connections
- Mock patches `sfwebui.SpiderFootDb` but does not intercept `spiderfoot/db/db_core.py` psycopg2.connect()
- Pre-commit hooks were blocked by these failures

---

## 5. Test Execution Reference

### 5.1 Unit Tests

```bash
# Quick run (interactive runner)
./test/run

# Direct pytest
python3 -m pytest test/unit/ -v

# With coverage
python3 -m pytest test/unit/ --cov=spiderfoot --cov-report=html --cov-report=xml
```

### 5.2 Integration Tests

```bash
# Excluding module integration tests
python3 -m pytest test/integration/ -k "not modules"

# All integration tests (requires API keys)
python3 -m pytest test/integration/
```

### 5.3 Module Integration Tests

```bash
python3 -m pytest -n auto --flake8 --dist loadfile --durations=5 \
    --cov-report html --cov=. test/integration/modules/
```

### 5.4 Full Suite (Parallel)

```bash
python3 -m pytest -n auto --flake8 --dist loadfile --durations=5 \
    --cov-report html --cov-report xml --cov=. .
```

### 5.5 Regression Tests

```bash
# All regression tests
python3 -m pytest test/regression/ -v

# Specific suite
python3 -m pytest test/regression/test_database_settings_persistence.py -v

# Only bug verification tests
python3 -m pytest test/regression/ -k "bug" -v
```

### 5.6 Acceptance Tests (E2E)

Requires SpiderFoot running on port 5001:

```bash
# Terminal 1: Start SpiderFoot
python3 ./sf.py -l 127.0.0.1:5001

# Terminal 2: Run Robot Framework
cd test/acceptance
robot --variable BROWSER:Firefox --outputdir results scan-firefox.robot
```

### 5.7 Docker-based

```bash
docker exec -it spiderfoot python3 -m pytest test/unit/ -v
```

---

## 6. Quality Tools Configuration

### 6.1 SonarQube

- **Project Key:** `number-two-scope`
- **Server:** `https://sonar.blk.ing`
- **Python:** 3.9-3.12
- **JavaScript/TypeScript:** Included
- **Test exclusions:** `test/**`, `*.test.*`

**What SonarQube detects:** Code smells, security vulnerabilities (SQL injection, XSS), bug patterns, duplication, complexity, unused variables/imports, hardcoded credentials.

**What SonarQube cannot detect:** API contract mismatches, runtime logic errors, frontend-backend integration issues, dynamic typing issues in JavaScript, missing properties in JSON responses.

### 6.2 Flake8 (`setup.cfg`)

- Max line length: 120
- Max complexity: 60
- Google docstring convention
- Selectors: C, E, F, W, B, B9, DAR, DUO, R, A, S, Q0, SIM, SFS
- Per-file ignores for modules, tests, and specific files
- SpiderFoot-specific plugin: flake8-sfs

### 6.3 Coverage (`.coveragerc`)

Minimal configuration — only omits template files (`spiderfoot_templates_*_tmpl`).

### 6.4 Pylint (`.pylintrc`)

- 4 parallel jobs
- Various checker configurations

---

## 7. Future/Aspirational Items (NOT YET IMPLEMENTED)

**Source:** `TESTING_AND_QA_GUIDE.md` (dated 2025-10-25)

The following items were proposed but have **not been built**:

| Item | Description | Status |
|------|-------------|--------|
| Pact contract testing | Consumer-driven API contract tests | Not implemented |
| JSON schema validation | Schema definitions for API responses | Not implemented |
| OpenAPI/Swagger spec | `spiderfoot/api/openapi.yaml` | Not implemented |
| TypeScript conversion | Type-safe frontend code | Not implemented |
| GitHub Actions CI/CD | `.github/workflows/quality-assurance.yml` | Not implemented |
| Pre-commit hooks | `.pre-commit-config.yaml` (black, flake8, eslint) | Not implemented |
| Selenium integration tests | UI workflow tests (multi-target scan flow) | Not implemented |
| API contract test directory | `test/contract/` | Not implemented |
| Schema definitions | `test/schemas/workspace_schemas.py` | Not implemented |

---

## 8. Remaining Work

### Priority 1: Fix the psycopg2 Mocking Issue

**Fix the root cause of the 143 WebUI test failures.**

The mock in `conftest.py` patches `psycopg2.connect` at the module level, but `db_core.py` may import psycopg2 before the patch takes effect, or the WebUI test base classes patch at the wrong location.

**Fix approach:** Ensure `psycopg2.connect` is patched before any SpiderFoot import, and that all test base classes use the conftest-level mock rather than their own incomplete patches.

### Priority 2: Verify Unit Tests Pass

```bash
python3 -m pytest test/unit/ -v --tb=short
```

Target: All unit tests pass with mocked database connections. Zero real psycopg2 connection attempts.

### Priority 3: Address Regression Test Gaps

From `REGRESSION_TEST_ANALYSIS_REPORT.md`, the remaining gaps:
- Concurrent access tests
- PostgreSQL integration test (sfp__stor_db uses saved settings)
- WebUI form submission integration test
- Settings page rendering verification
- CSRF token validation with settings save
- Database transaction rollback on failure

### Priority 4: Implement Aspirational Items

From `TESTING_AND_QA_GUIDE.md`, in priority order:
1. Pre-commit hooks (`.pre-commit-config.yaml`)
2. GitHub Actions CI/CD workflow
3. JSON schema validation for API responses
4. API contract tests
5. OpenAPI specification

---

## 9. As-Is Documentation Suite

The `spiderfoot-as-is-documentation/` directory contains a reverse-engineered documentation effort (2025-11-02):

- 47+ functional requirements with traceability matrix
- 30+ specifications reverse-engineered from 590 test files
- 20 Mermaid architecture diagrams
- Regression registry with structured tracking process

This documentation references the test suite extensively (590 files, 683 test functions, 985+ assertions with file/line references).

---

## 10. Superseded Documents

The following documents are superseded by this test plan. They remain in the repository for historical reference:

| Document | Why Superseded |
|----------|---------------|
| `TESTING_AND_QA_GUIDE.md` | Aspirational content presented as current; no clear separation of implemented vs. planned |
| `REGRESSION_TEST_SUMMARY.md` | Narrow scope (one bug) |
| `REGRESSION_TEST_ANALYSIS_REPORT.md` | Narrow scope (one bug); analysis/recommendations only |
| `test/README.md` | Content incorporated into this test plan |
| `test/TODO.md` | Incomplete plan for test runner script; content incorporated here |
| `test/regression/README.md` | Regression test standards incorporated here |
