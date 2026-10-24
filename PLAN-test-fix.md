# SpiderFoot Test Infrastructure Fix Plan

**Date:** 2026-03-02
**Author:** Claude (Engineering Agent)
**Status:** DRAFT — Awaiting HMFIC Approval

---

## 1. Current State Assessment

### 1.1 Test Results Snapshot (2026-03-02)

| Suite | Passed | Failed | Skipped | Hung | Total |
|-------|--------|--------|---------|------|-------|
| Unit (excl. WebUI) | 2,357 | 63 | 259 | 0 | 2,679 |
| Unit WebUI | 0 | 0 | 0 | ~262 | ~262 |
| Integration | 18 | 0 | 64 | 0 | 82 |
| **TOTAL** | **2,375** | **63** | **323** | **~262** | **~3,023** |

### 1.2 Root Causes Identified

| # | Category | Root Cause | Impact |
|---|----------|-----------|--------|
| RC-1 | WebUI Hung (262 tests) | `test_webui_base.py` patches `sfwebui.SpiderFootDb` but doesn't intercept `psycopg2.connect()` in `spiderfoot/db/db_core.py` — real DB connection attempted, hangs xdist workers | **CRITICAL** — blocks entire test run when included |
| RC-2 | Scan API failures (33 tests) | Mock interface drift — `test_sfapi_scan_api.py` and `test_sfapi_scan_api_extra.py` mock `SpiderFootDb` with stale method signatures (`AttributeError`) | HIGH |
| RC-3 | Enhanced scanner failures (3 tests) | `test_enhanced_scanner_with_threadreaper.py` — resource leak detection, start/stop, invalid modules failures | MEDIUM |
| RC-4 | SF API core failures (2 tests) | `test_sfapi.py` config class instantiation and app config function broken | MEDIUM |
| RC-5 | Miscellaneous failures (25 tests) | Nmap tool path, cross-platform stability, sf_main edge case | LOW-MEDIUM |
| RC-6 | Integration skips (64 tests) | "Requires integration DB with write permissions to schema public" — permission check too strict | LOW |
| RC-7 | Missing `.env.test` file | conftest references it in error message but file doesn't exist | LOW |
| RC-8 | User name mismatch | conftest defaults `spiderfoot_test`, setup script creates `spiderfoot` | LOW |

---

## 2. Plan Structure (ITKR-TEMP Methodology Applied)

Following the ITKR Phase 9 Test Management approach:
- **Entry Criteria** per fix phase
- **Verification Method** for each fix
- **Exit Criteria** = green test run
- **RTM**: Each fix maps to a defect ID traceable to a test file

---

## 3. Fix Phases

### Phase 1: Infrastructure (P0 — Do First)

**Objective:** Create the `.env.test` file and fix user/naming inconsistencies so tests can be invoked consistently.

| Task | File(s) | Action |
|------|---------|--------|
| 1.1 | `.env.test` | Create with correct env vars (reference 1Password DEV_VAULT for password via `op://` URI) |
| 1.2 | `test/setup_test_db.sh` | Align user name: change default to match conftest or vice versa |
| 1.3 | `test/conftest.py:216` | Fix `db_owner` default from `spiderfoot_test` → `spiderfoot` (matches what setup script creates) |
| 1.4 | `pytest.ini` | Verify timeout and worker count are sane |

**Entry Criteria:** PostgreSQL container running, test DB exists
**Exit Criteria:** `op run --env-file='./.env.test' -- python3 -m pytest --co -q` collects all 2941 tests without error

**Verification:** Run test collection, confirm no `EnvironmentError`

---

### Phase 2: WebUI Test Mock Fix (P0 — Critical)

**Objective:** Fix the 262 hung WebUI tests by intercepting DB connections at the correct level.

| Task | File(s) | Action |
|------|---------|--------|
| 2.1 | Investigate | Read `spiderfoot/db/db_core.py` to find exact `psycopg2.connect()` call path |
| 2.2 | Investigate | Read `test/unit/utils/test_webui_base.py` to understand current mock strategy |
| 2.3 | Investigate | Read `test/unit/test_sfwebui.py` to understand test structure |
| 2.4 | Fix | Patch `psycopg2.connect` at the module level in db_core.py, not at the `sfwebui.SpiderFootDb` level |
| 2.5 | Fix | Ensure mock returns a proper MagicMock connection with cursor(), execute(), fetchall(), etc. |
| 2.6 | Fix | Add `@pytest.fixture` that provides a mock DB for all WebUI tests |
| 2.7 | Verify | Run `test/unit/test_sfwebui.py` with timeout — all tests should complete (pass or fail, NOT hang) |
| 2.8 | Verify | Run `test/unit/test_sfwebui_enhanced.py` same verification |

**Entry Criteria:** Phase 1 complete
**Exit Criteria:** All WebUI tests complete within 30s timeout each (no hangs)
**Verification:** `pytest test/unit/test_sfwebui.py test/unit/test_sfwebui_enhanced.py --timeout=30 -q` finishes

---

### Phase 3: Scan API Mock Alignment (P1)

**Objective:** Fix 33 scan API test failures caused by mock interface drift.

| Task | File(s) | Action |
|------|---------|--------|
| 3.1 | Investigate | Read `test/unit/test_sfapi_scan_api.py` — identify which `AttributeError` methods are missing |
| 3.2 | Investigate | Read current `SpiderFootDb` class to get actual method signatures |
| 3.3 | Fix | Update mock objects in scan API tests to match current DB interface |
| 3.4 | Fix | Update assertion targets in `test_sfapi_scan_api_extra.py` |
| 3.5 | Verify | Run scan API tests in isolation |

**Entry Criteria:** Phase 2 complete (or parallel if independent)
**Exit Criteria:** All 33 scan API tests pass
**Verification:** `pytest test/unit/test_sfapi_scan_api.py test/unit/test_sfapi_scan_api_extra.py -q`

---

### Phase 4: Enhanced Scanner & SF API Core (P2)

**Objective:** Fix 5 remaining test failures.

| Task | File(s) | Action |
|------|---------|--------|
| 4.1 | `test/unit/test_enhanced_scanner_with_threadreaper.py` | Debug resource leak detection, start/stop cycle, invalid modules |
| 4.2 | `test/unit/test_sfapi.py` | Fix config class instantiation and app config function |
| 4.3 | `test/unit/test_sf_main.py` | Fix abort exception handling edge case |
| 4.4 | `test/unit/test_cross_platform_stability.py` | Fix empty target validation |
| 4.5 | `test/unit/modules/test_sfp_tool_nmap.py` | Fix nmap tool path error state test |

**Entry Criteria:** Phase 3 complete
**Exit Criteria:** All 5 tests pass
**Verification:** Run each test file individually

---

### Phase 5: Integration Test Permissions (P3)

**Objective:** Fix 64 skipped integration tests.

| Task | File(s) | Action |
|------|---------|--------|
| 5.1 | Investigate | Find the skip condition — likely checking schema write permissions |
| 5.2 | Fix | Grant proper schema permissions via setup_test_db.sh or conftest fixture |
| 5.3 | Verify | Run integration tests, confirm skips are eliminated |

**Entry Criteria:** Phase 4 complete
**Exit Criteria:** ≤10 integration tests skipped (only those requiring external APIs)
**Verification:** `pytest test/integration/ -q`

---

### Phase 6: Full Regression & Cleanup (P3)

**Objective:** Full green test suite run, documentation updated.

| Task | File(s) | Action |
|------|---------|--------|
| 6.1 | Run full suite | `op run --env-file='./.env.test' -- python3 -m pytest` |
| 6.2 | Document | Update `PROJECT.STATUS.md` with test results |
| 6.3 | Commit | Stage and commit all fixes |

**Entry Criteria:** All previous phases complete
**Exit Criteria:** Full test suite passes (0 failures, 0 hangs)
**Verification:** Complete run with coverage report

---

## 4. Requirements Traceability

Mapping fix tasks to the ITKR-TEMP DT&E methodology (Section 4.1):

| Fix Phase | ITKR Equivalent | Verification Level |
|-----------|-----------------|-------------------|
| Phase 1 (Infra) | Test Environment Readiness (TRR 3.2) | Configuration verification |
| Phase 2 (WebUI mocks) | Unit Test (DT&E 4.1) | Unit test execution |
| Phase 3 (API mocks) | Unit Test (DT&E 4.1) | Unit test execution |
| Phase 4 (Scanner/Core) | Integration Test (DT&E 4.2) | Component interaction |
| Phase 5 (Integration perms) | System Integration (DT&E 4.3) | Database integration |
| Phase 6 (Regression) | Regression (QA Phase 5) | Full suite |

---

## 5. Execution Strategy

- **Phases 1-2:** Sequential (Phase 2 depends on Phase 1 infrastructure)
- **Phases 3-4:** Can be parallelized via subagents (independent test files)
- **Phase 5:** Sequential after 3-4 (integration depends on unit stability)
- **Phase 6:** Final sequential gate

**Estimated effort:** ~2-3 hours of focused work across all phases.

---

## 6. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| WebUI mock fix reveals deeper architectural coupling to DB | Medium | High | If mocking at psycopg2 level insufficient, may need to refactor db_core.py dependency injection |
| Scan API tests need complete rewrite (not just mock alignment) | Low | Medium | Read actual API code first to understand drift magnitude |
| Integration test permissions fix breaks production DB | Low | High | All operations scoped to `spiderfoot_test` DB only |

---

## 7. Quality Gate Criteria (from /stuff/coding_standards)

Before claiming any phase complete:
- [ ] Tests executed (not just written)
- [ ] Linter run on modified files
- [ ] No error suppression (no `2>/dev/null`)
- [ ] Graceful error handling (no bare except, no fallbacks)
- [ ] Results verified with raw output shown to HMFIC
