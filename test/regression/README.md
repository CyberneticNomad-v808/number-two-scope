# SpiderFoot Regression Test Suite

This directory contains regression tests for critical bugs that have been fixed in SpiderFoot.

## Purpose

Regression tests ensure that bugs, once fixed, do not reappear in future versions. Each test suite in this directory:
1. Reproduces the original bug behavior
2. Verifies the fix works correctly
3. Tests edge cases and error conditions
4. Provides comprehensive coverage

## Current Test Suites

### Database Settings Persistence (`test_database_settings_persistence.py`)

**Bug:** Module settings (specifically sfp__stor_db PostgreSQL connection settings) were not persisting when saved through the WebUI settings page.

**Root Cause:** In `spiderfoot/webui/routes.py`, modules were being loaded AFTER attempting to unserialize config from the database. This meant there was no reference point for module settings.

**Fix:** Moved module loading to happen BEFORE database config unserialization in WebUiRoutes.__init__.

**Test Coverage:**
- 21 test methods across 5 test classes
- Bug reproduction and fix validation
- Error handling and edge cases
- Integration tests with WebUI

**Critical Tests:**
- `TestBugVerification::test_original_bug_modules_not_loaded_first` - Must fail if bug reintroduced
- `TestBugVerification::test_modules_loaded_before_database_config_restored` - Verifies loading order

## Running Tests

### Run All Regression Tests
```bash
cd /stuff/spiderfoot
python -m pytest test/regression/ -v
```

### Run Specific Test Suite
```bash
python -m pytest test/regression/test_database_settings_persistence.py -v
```

### Run with Coverage Report
```bash
python -m pytest test/regression/ --cov=spiderfoot --cov-report=html
open htmlcov/index.html
```

### Run Only Critical Tests
```bash
python -m pytest test/regression/ -k "bug" -v
```

## Test Output Example

```
test/regression/test_database_settings_persistence.py::TestBugVerification::test_original_bug_modules_not_loaded_first PASSED
test/regression/test_database_settings_persistence.py::TestBugVerification::test_module_loading_order_in_webui_routes PASSED
test/regression/test_database_settings_persistence.py::TestErrorConditions::test_invalid_type_conversion_handled_gracefully PASSED
...
========================= 27 tests passed in 8.42s =========================
```

## Adding New Regression Tests

When you fix a critical bug:

1. **Create a new test file** (or add to existing)
   ```python
   # test/regression/test_your_bug_name.py
   ```

2. **Include these test classes:**
   - `TestBugVerification` - Reproduce bug and verify fix
   - `TestErrorConditions` - Edge cases
   - `TestIntegration` - End-to-end scenarios

3. **Critical requirements:**
   - At least one test that reproduces the original bug
   - At least one test that verifies the fix mechanism
   - Tests must fail if bug is reintroduced

4. **Document the bug:**
   ```python
   """
   Regression tests for [bug name].

   Bug: [description]
   Root Cause: [technical cause]
   Fix: [what was changed]
   """
   ```

## Test Quality Standards

All regression tests must:
- ✅ Be fully isolated (no shared state between tests)
- ✅ Clean up resources (temp files, database connections)
- ✅ Run quickly (< 10 seconds per test)
- ✅ Be deterministic (no flaky tests)
- ✅ Have clear failure messages
- ✅ Test both positive and negative cases

## CI/CD Integration

Regression tests run automatically on:
- Every push to main branch
- Every pull request
- Nightly builds

**Failure Policy:** Any regression test failure blocks the merge/deployment.

## Maintenance

- Review regression tests quarterly
- Update tests when related code is refactored
- Add new tests for any critical bug fix
- Remove tests only if the feature is completely removed

## Documentation

- **Detailed Analysis:** `/stuff/spiderfoot/REGRESSION_TEST_ANALYSIS_REPORT.md`
- **Summary:** `/stuff/spiderfoot/REGRESSION_TEST_SUMMARY.md`
- **Main Testing Guide:** `/stuff/spiderfoot/TESTING_AND_QA_GUIDE.md`

## Questions?

Contact the QA team or refer to the comprehensive testing guide.

---

**Last Updated:** 2025-10-29
**Test Count:** 27 tests across 1 suite
**Coverage:** ~85% of critical paths
