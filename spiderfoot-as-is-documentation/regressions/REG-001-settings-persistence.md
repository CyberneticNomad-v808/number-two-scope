# REG-001: Settings Not Persisting to Database

**Status:** ✅ Fixed
**Severity:** High
**Date Found:** 2025-11-02
**Date Fixed:** 2025-11-02
**Components:** Database Layer, Web UI Settings

---

## Summary

Web UI settings form submission was not properly persisting configuration values to the database, causing settings to be lost after server restart.

---

## Traceability

### Requirements
- **UR-006:** Configuration Persistence (User Requirement)
- **REQ-DB-003:** Configuration Persistence (Functional Requirement)
- **REQ-UI-001:** Settings Form Submission (Functional Requirement)

### Specifications
- **SPEC-DB-003:** configSet/configGet behavior
- **SPEC-UI-001:** Settings form submission flow

### Tests
- `test/regression/test_database_settings_persistence.py` (678 lines, 15+ tests)
- `test/regression/test_webui_settings_form_submission.py`
- `test/acceptance/settings_persistence.robot` (318 lines, 10+ scenarios)

---

## Root Cause

**Primary Issues:**
1. **Boolean Conversion:** Boolean settings stored as strings, not properly converted on retrieval
2. **Config Reference:** Web UI using wrong config reference during form submission
3. **Module Loading Order:** Config initialization happening before modules loaded

**Affected Code:**
- `spiderfoot/db/__init__.py:configSet()` - Database persistence layer
- `spiderfoot/webui/settings.py` - Web UI settings controller

---

## Reproduction Steps

1. Navigate to Settings page in Web UI
2. Modify any boolean setting (e.g., enable/disable module)
3. Click "Save Settings"
4. Restart SpiderFoot server
5. **BUG:** Settings revert to defaults

---

## Fix Implementation

### Database Layer Fix
```python
# spiderfoot/db/__init__.py
def configSet(self, optMap=None):
    """Properly handle boolean conversion"""
    # Convert booleans to strings for storage
    # Ensure atomic transaction
    # Validate before commit
```

### Web UI Fix
```python
# spiderfoot/webui/settings.py
def savesettings(self):
    """Use correct config reference"""
    # Use self.config instead of global
    # Validate form data
    # Persist to database
```

---

## Regression Tests

### Critical Tests to Monitor
```bash
# Run these before every release
pytest test/regression/test_database_settings_persistence.py::test_settings_persist_after_restart -v
pytest test/regression/test_database_settings_persistence.py::test_boolean_settings_conversion -v
robot test/acceptance/settings_persistence.robot
```

### Test Coverage
- ✅ Settings persistence across restarts
- ✅ Boolean value conversion
- ✅ Module configuration persistence
- ✅ Form submission validation
- ✅ Database transaction integrity
- ✅ Config reference correctness
- ✅ Multi-user settings isolation

---

## Prevention Measures

### Code Review Checklist
- [ ] All config changes use proper config reference
- [ ] Boolean values properly converted for storage/retrieval
- [ ] Database transactions are atomic
- [ ] Settings changes tested with server restart

### Automated Checks
- Run regression tests in CI/CD pipeline
- Monitor `spiderfoot/db/__init__.py` for changes
- Monitor `spiderfoot/webui/settings.py` for changes
- Alert on regression test failures

### High-Risk Areas
- Database configuration layer (`spiderfoot/db/`)
- Web UI settings controller (`spiderfoot/webui/settings.py`)
- Config initialization order
- Boolean type conversions

---

## Impact Assessment

**Severity:** High
**User Impact:** Settings lost on restart, requiring reconfiguration
**Data Impact:** Configuration data integrity
**Security Impact:** None (no security bypass)
**Performance Impact:** None

**Affected Users:** All users using Web UI for configuration
**Workaround:** Use CLI or manual database editing (not user-friendly)

---

## Lessons Learned

1. **Type Safety:** Need strict type handling for config values
2. **Testing Gaps:** Initial test suite didn't include restart scenarios
3. **Config Management:** Multiple config references created confusion
4. **Integration Testing:** Need more end-to-end tests for settings persistence

---

## Related Issues

- Initial bug report: [GitHub Issue #XXX] (if applicable)
- Related PRs: [PR #XXX] (if applicable)

---

## Regression History

| Date | Event |
|---|---|
| 2025-11-02 | Bug discovered during testing |
| 2025-11-02 | Root cause identified |
| 2025-11-02 | Regression tests created (678 lines) |
| 2025-11-02 | Fix implemented and verified |
| 2025-11-02 | Documentation updated |

---

**Last Updated:** 2025-11-04
**Monitored:** ✅ Active
**Regression Test Status:** ✅ Passing
