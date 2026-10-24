# Regression Registry

**Purpose:** Track known regressions with full traceability to specs, requirements, and tests
**Status:** Active
**Last Updated:** 2025-11-04

---

## Overview

This registry maintains a living record of all regressions discovered in SpiderFoot. Each regression entry includes:
- Full traceability chain (Requirement → Spec → Tests)
- Root cause analysis
- Prevention measures
- Regression test references

---

## Active Regressions

| ID | Title | Severity | Status | Date Found | Date Fixed | Tests |
|---|---|---|---|---|---|---|
| REG-001 | Settings Not Persisting to Database | High | Fixed | 2025-11-02 | 2025-11-02 | ✅ 15 tests |

---

## Regression Summary

**Total Regressions:** 1
**Fixed:** 1
**Open:** 0
**Critical:** 0
**High:** 1
**Medium:** 0
**Low:** 0

---

## Regression Coverage

**With Tests:** 1/1 (100%)
**Test Files:** 3
**Total Test Cases:** 15+

---

## High-Risk Areas

Areas with multiple regressions or high-severity issues:

1. **Database Configuration Persistence** (REG-001)
   - Components: Database Layer, Web UI Settings
   - Risk Level: High
   - Prevention: Monitor config layer changes, run regression tests

---

## Regression Test Suites

### Critical Regression Tests
Run before every release:

```bash
# Database configuration persistence
pytest test/regression/test_database_settings_persistence.py -v
pytest test/regression/test_webui_settings_form_submission.py -v
robot test/acceptance/settings_persistence.robot
```

---

## Monitoring Guidelines

### When to Track a Regression
- Bug was previously fixed but reoccurred
- Bug affects core functionality
- Bug has data integrity implications
- Bug bypasses security controls
- Bug affects multiple components

### When to Create Regression Tests
- Always for critical/high severity bugs
- When bug has clear reproduction steps
- When bug affects documented requirements
- When bug could easily reoccur

### Regression Entry Requirements
- [ ] Bug description
- [ ] Traceability to specs/requirements
- [ ] Test references (existing or new)
- [ ] Root cause analysis
- [ ] Prevention measures

---

## Regression Entries

### REG-001: Settings Not Persisting to Database
**File:** [REG-001-settings-persistence.md](REG-001-settings-persistence.md)
**Status:** ✅ Fixed
**Severity:** High
**Components:** Database Layer, Web UI
**Requirements:** REQ-DB-003, REQ-UI-001, UR-006
**Specs:** SPEC-DB-003, SPEC-UI-001
**Tests:** 15+ regression tests

---

## Usage

### Track New Regression
```bash
/regression-track "Bug description here"
```

### Validate Regression Tests
```bash
/spec-validate spiderfoot-as-is
```

### Run All Regression Tests
```bash
pytest test/regression/ -v
robot test/acceptance/*.robot
```

---

## Maintenance

**Update Frequency:** After each bug fix or new regression discovery
**Review Schedule:** Weekly during active development
**Cleanup Policy:** Keep fixed regressions indefinitely for historical tracking

---

## Metrics

### Regression Detection
- **Mean Time to Detect:** Track how quickly regressions are caught
- **Detection Method:** Manual testing, automated tests, user reports

### Regression Resolution
- **Mean Time to Fix:** Track resolution speed
- **Prevention Success:** Track re-occurrence rate

---

**Last Registry Update:** 2025-11-04
**Registry Maintained By:** Development Team
