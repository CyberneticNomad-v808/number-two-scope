# Documentation Location

**Current Location:** `/stuff/spiderfoot/spiderfoot-as-is-documentation/`
**Previous Location:** `.trash/spiderfoot-as-is-documentation/` (restored 2026-02-06)
**Original Location:** `.claude/specs/spiderfoot-as-is/` (deprecated)
**Date Restored:** 2026-02-06

---

## Why This Location?

This documentation lives in the SpiderFoot project root alongside the code it documents. A planned move to `/stuff/coding_standards/` was never completed.

---

## Structure

```
/stuff/spiderfoot/spiderfoot-as-is-documentation/
├── README.md                           # Quick start guide
├── INDEX.md                            # Complete documentation index
├── SUMMARY.md                          # Project completion summary
├── LOCATION.md                         # This file
│
├── design/
│   ├── 01-system-architecture.md       # Architecture + 20 diagrams
│   └── 02-specifications-from-tests.md # 30+ specifications
│
├── requirements/
│   └── 01-functional-requirements.md   # 47+ requirements
│
├── regressions/
│   ├── REGISTRY.md                     # Regression tracking registry
│   └── REG-*.md                        # Individual regression entries
│
├── diagrams/                           # (Future: extracted diagrams)
└── tasks/                              # (Future: implementation tasks)
```

---

## Related Commands

### Slash Commands (in `.claude/commands/`)
- `/regression-track "bug description"` - Track new regressions
- `/spec-validate [feature-name]` - Validate documentation health

These commands have been updated to point to this new location.

---

## Access

**From SpiderFoot project:**
```bash
cd /stuff/spiderfoot/spiderfoot-as-is-documentation/
```

**From anywhere:**
```bash
cd /stuff/spiderfoot/spiderfoot-as-is-documentation/
```

---

## Maintenance

When updating documentation:
1. Update files in this location (`/stuff/spiderfoot/spiderfoot-as-is-documentation/`)
2. Do NOT update the old `.claude/specs/` location
3. Use `/spec-validate` to check health after updates
4. Update regression registry when tracking new bugs

---

**Last Updated:** 2026-02-06
