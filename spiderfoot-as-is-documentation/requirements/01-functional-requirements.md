# SpiderFoot Functional Requirements

**Version:** 1.0
**Date:** 2025-11-02
**Status:** Derived from Test Suite and Design
**Traceability:** Tests → Specifications → Requirements

---

## Table of Contents

1. [Overview](#overview)
2. [User Requirements](#user-requirements)
3. [System Requirements](#system-requirements)
4. [Functional Requirements by Component](#functional-requirements-by-component)
5. [Non-Functional Requirements](#non-functional-requirements)
6. [Requirements Traceability Matrix](#requirements-traceability-matrix)

---

## Overview

This document contains functional requirements for SpiderFoot, derived through reverse engineering from:
1. **Test Suite Analysis** (590 test files, ~55,177 lines)
2. **Design Documentation** (architecture, specifications)
3. **Code Analysis** (implementation patterns)

**Requirement Format:**
```
REQ-[COMPONENT]-[NUMBER]: [Title]
Priority: [High|Medium|Low]
Source: [Test file or design doc]
Verification: [How to verify]
```

---

## User Requirements

### UR-001: OSINT Data Collection
i df**Description:** As an analyst, I need to automatically collect intelligence from multiple sources about a target.

**Acceptance Criteria:**
- System SHALL collect data from 270+ OSINT sources
- System SHALL support targets: domains, IPs, emails, netblocks
- System SHALL recursively discover related entities
- Results SHALL be stored for analysis

**Source:** Project scope, module tests
**Priority:** High

---

### UR-002: Intelligence Correlation
**Description:** As an analyst, I need automated correlation to identify patterns and risks.

**Acceptance Criteria:**
- System SHALL correlate events across data sources
- System SHALL identify high-risk patterns (compromised emails, open databases)
- System SHALL aggregate related findings
- System SHALL assign risk levels (INFO, LOW, MEDIUM, HIGH)

**Source:** Correlation engine design, correlation tests
**Priority:** High

---

### UR-003: Multiple Access Interfaces
**Description:** As a user, I need flexible ways to interact with the system.

**Acceptance Criteria:**
- System SHALL provide Web UI for interactive use
- System SHALL provide REST API for programmatic access
- System SHALL provide CLI for scripting and automation
- Interfaces SHALL provide equivalent functionality

**Source:** Architecture design, UI/API/CLI tests
**Priority:** High

---

### UR-004: Scan Management
**Description:** As an analyst, I need to manage multiple concurrent scans.

**Acceptance Criteria:**
- System SHALL support multiple simultaneous scans
- System SHALL persist scan results permanently
- System SHALL allow scan deletion
- System SHALL show scan status in real-time

**Source:** Scanner tests, acceptance tests
**Priority:** High

---

### UR-005: Data Export
**Description:** As an analyst, I need to export findings in multiple formats.

**Acceptance Criteria:**
- System SHALL export to CSV format
- System SHALL export to JSON format
- System SHALL export to Excel (XLSX) format
- System SHALL export graph data (GEXF) format
- Exports SHALL include all scan data

**Source:** Export functionality tests, WebUI tests
**Priority:** Medium

---

### UR-006: Configuration Persistence
**Description:** As an administrator, I need settings to persist across restarts.

**Acceptance Criteria:**
- System SHALL save configuration to database
- Configuration SHALL survive application restart
- Configuration SHALL support module-specific settings
- System SHALL handle boolean, integer, and string types correctly

**Source:** `test_database_settings_persistence.py`, `settings_persistence.robot`
**Priority:** High
**Critical:** YES (was a major bug)

---

## System Requirements

### SR-001: Python Runtime
**Description:** System SHALL run on Python 3.11+
**Source:** Dockerfile, requirements.txt
**Priority:** High

---

### SR-002: Database Support
**Description:** System SHALL support SQLite and PostgreSQL databases
**Source:** Database layer design, db tests
**Priority:** High

---

### SR-003: Multi-Process Architecture
**Description:** System SHALL support concurrent scan execution via multiprocessing
**Source:** Architecture design, scanner tests
**Priority:** High

---

### SR-004: Containerization
**Description:** System SHALL be deployable via Docker
**Source:** Dockerfile, docker-compose.yml
**Priority:** Medium

---

### SR-005: Cross-Platform Support
**Description:** System SHALL run on Linux, macOS, and Windows
**Source:** Platform utils tests, CI configuration
**Priority:** Medium

---

## Functional Requirements by Component

## Core Library Requirements

### REQ-CORE-001: Initialization with Configuration
**Description:** Core SpiderFoot class SHALL initialize with configuration dictionary
**Priority:** High
**Source:** `test/unit/test_spiderfoot.py:35`
**Specification:** SPEC-CORE-001

**Requirements:**
1. SHALL accept dict type for options parameter
2. SHALL accept empty dict {} as valid input
3. SHALL raise TypeError if options is not dict
4. SHALL initialize dbh, scanId, socksProxy properties

**Verification:**
```python
sf = SpiderFoot({})  # Must not raise exception
assert hasattr(sf, 'dbh')
assert hasattr(sf, 'scanId')
```

---

### REQ-CORE-002: Option Value Resolution
**Description:** System SHALL resolve option values from files, URLs, or literals
**Priority:** Medium
**Source:** `test/unit/test_sflib.py:123`
**Specification:** SPEC-CORE-002

**Requirements:**
1. SHALL return string values as-is
2. SHALL load file contents when value starts with '@'
3. SHALL fetch URL contents for HTTP/HTTPS URLs
4. SHALL return None for invalid types
5. SHALL return None gracefully if file not found
6. SHALL return None gracefully if network error

**Verification:**
```python
sf.optValueToData("plain") == "plain"
sf.optValueToData("@VERSION") == file_contents
sf.optValueToData(None) == None
```

**Traceability:**
- Derived from: SPEC-CORE-002
- Tests: `test_optValueToData_*`
- Design: Core architecture, configuration management

---

### REQ-CORE-003: Cryptographic Hashing
**Description:** System SHALL provide SHA-256 hashing for string values
**Priority:** High
**Source:** `test/unit/test_sflib.py:173`
**Specification:** SPEC-CORE-003

**Requirements:**
1. SHALL use SHA-256 algorithm
2. SHALL return lowercase hexadecimal string
3. SHALL return exactly 64 characters
4. SHALL be deterministic (same input → same output)
5. SHALL be used for event deduplication

**Verification:**
```python
hash_val = sf.hashstring("example string")
assert len(hash_val) == 64
assert hash_val == "aedfb92b3053a21a114f4f301a02a3c6ad5dff504d124dc2cee6117623eec706"
```

**Traceability:**
- Derived from: SPEC-CORE-003
- Tests: `test_hashstring_*`
- Design: Event system, deduplication logic

---

### REQ-CORE-004: URL Parsing
**Description:** System SHALL extract FQDN from URLs
**Priority:** Medium
**Source:** `test/unit/test_sflib.py:297`
**Specification:** SPEC-CORE-004

**Requirements:**
1. SHALL extract hostname from valid URLs
2. SHALL remove protocol (http://, https://)
3. SHALL remove port numbers
4. SHALL remove path components
5. SHALL return None for invalid URLs

**Verification:**
```python
sf.urlFQDN("http://localhost.local:8080/path") == "localhost.local"
sf.urlFQDN("invalid") == None
```

---

### REQ-CORE-005: Logging Infrastructure
**Description:** System SHALL provide structured logging with multiple levels
**Priority:** High
**Source:** `test/unit/test_spiderfoot.py`
**Specification:** SPEC-CORE-005

**Requirements:**
1. SHALL provide error() method that DOES NOT exit
2. SHALL provide status() method for status messages
3. SHALL provide info() method for informational messages
4. SHALL provide debug() method controlled by _debug option
5. SHALL provide fatal() method that calls sys.exit(-1)
6. Logging methods SHALL NOT raise exceptions

**Verification:**
```python
sf.error("test")  # Must not call sys.exit()
sf.info("test")   # Must not raise exception
# fatal() should exit
with pytest.raises(SystemExit):
    sf.fatal("fatal error")
```

---

### REQ-CORE-006: Module Discovery
**Description:** System SHALL discover and query module capabilities
**Priority:** High
**Source:** `test/unit/test_sflib.py`

**Requirements:**
1. SHALL list modules producing specific event types
2. SHALL list modules consuming specific event types
3. SHALL list events produced by specific modules
4. SHALL list events consumed by specific modules
5. SHALL return empty list for no matches

**Verification:**
```python
producers = sf.modulesProducing(["IP_ADDRESS"])
assert isinstance(producers, list)

consumers = sf.modulesConsuming(["INTERNET_NAME"])
assert isinstance(consumers, list)
```

---

## Database Requirements

### REQ-DB-001: Database Initialization
**Description:** System SHALL initialize database with required configuration
**Priority:** High
**Source:** `test/unit/spiderfoot/test_spiderfootdb.py:35`
**Specification:** SPEC-DB-001

**Requirements:**
1. SHALL require dict type for opts parameter
2. SHALL require non-empty opts dict
3. SHALL require '__database' key in opts
4. SHALL support '__dbtype' values: 'sqlite', 'postgresql'
5. SHALL raise TypeError for invalid opts type
6. SHALL raise ValueError for empty opts or missing keys

**Verification:**
```python
# Valid initialization
db = SpiderFootDb({'__database': '/path/to/db', '__dbtype': 'sqlite'})

# Invalid initializations
with pytest.raises(TypeError):
    SpiderFootDb(None)

with pytest.raises(ValueError):
    SpiderFootDb({})
```

---

### REQ-DB-002: Schema Creation
**Description:** System SHALL create database schema with all required tables
**Priority:** High
**Source:** `test/unit/spiderfoot/test_spiderfootdb.py`
**Specification:** SPEC-DB-002

**Requirements:**
1. SHALL create 8 tables: tbl_event_types, tbl_config, tbl_scan_instance, tbl_scan_log, tbl_scan_config, tbl_scan_results, tbl_scan_correlation_results, tbl_scan_correlation_results_events
2. SHALL create 4 indexes: i1, i2, i3, i4
3. SHALL populate tbl_event_types with 389 event definitions
4. SHALL be idempotent (safe to call multiple times)
5. SHALL support both SQLite and PostgreSQL

**Verification:**
```python
db.create()
# Verify tables exist
tables = db.query("SELECT name FROM sqlite_master WHERE type='table'")
assert len(tables) == 8

# Verify event types populated
event_types = db.query("SELECT COUNT(*) FROM tbl_event_types")
assert event_types[0][0] == 389
```

---

### REQ-DB-003: Configuration Persistence
**Description:** System SHALL persist configuration to database with type conversion
**Priority:** High
**Source:** `test/regression/test_database_settings_persistence.py`
**Specification:** SPEC-DB-003

**Requirements:**
1. SHALL store configuration in tbl_config table
2. SHALL convert bool True → string "1"
3. SHALL convert bool False → string "0"
4. SHALL convert int → string
5. SHALL preserve string values
6. SHALL retrieve configuration with reverse type conversion
7. SHALL support module-specific settings (format: "module:option")
8. SHALL preserve special characters (Unicode, quotes, emoji)
9. SHALL persist across application restarts

**Verification:**
```python
# Store configuration
config = {'enable_feature': True, 'port': 5432, 'host': 'localhost'}
db.configSet(config)

# Verify stored as strings
raw = db.query("SELECT val FROM tbl_config WHERE opt='enable_feature'")
assert raw[0][0] == '1'

# Retrieve with type conversion
retrieved = db.configGet()
assert retrieved['enable_feature'] is True
assert retrieved['port'] == 5432
assert retrieved['host'] == 'localhost'
```

**Traceability:**
- Derived from: SPEC-DB-003
- Tests: `test_database_settings_persistence.py`, `test_webui_settings_form_submission.py`
- Design: Database layer, configuration management
- Bug Fix: Critical regression test for settings persistence bug

---

### REQ-DB-004: Scan Instance Management
**Description:** System SHALL manage scan instances with full lifecycle
**Priority:** High
**Source:** `test/unit/spiderfoot/test_spiderfootdb.py`
**Specification:** SPEC-DB-004

**Requirements:**
1. SHALL create scan instances with unique IDs
2. SHALL store: name, target, targetType, status, timestamps
3. SHALL support status values: INITIALIZING, STARTING, RUNNING, FINISHED, ERROR-FAILED, ABORTED
4. SHALL retrieve scan instance details by ID
5. SHALL list all scan instances
6. SHALL delete scan instances with cascade to related data
7. SHALL track created, started, ended timestamps

**Verification:**
```python
# Create scan
scanId = str(uuid.uuid4())
db.scanInstanceCreate(scanId, "Test Scan", "example.com")

# Retrieve
scan = db.scanInstanceGet(scanId)
assert scan[0] == "Test Scan"
assert scan[1] == "example.com"

# Delete with cascade
db.scanInstanceDelete(scanId)
# Verify events deleted
events = db.scanResultEvent(scanId)
assert len(events) == 0
```

---

### REQ-DB-005: Event Storage and Retrieval
**Description:** System SHALL store and retrieve scan events with metadata
**Priority:** High
**Source:** `test/unit/spiderfoot/test_spiderfootdb.py`
**Specification:** SPEC-DB-005

**Requirements:**
1. SHALL store events in tbl_scan_results
2. SHALL store: type, data, module, confidence, visibility, risk, hash
3. SHALL use event hash for deduplication
4. SHALL support data truncation for large events
5. SHALL retrieve events by scan ID
6. SHALL filter events by type
7. SHALL maintain event chains via source_event_hash
8. SHALL store confidence, visibility, risk as 0-100 integers

**Verification:**
```python
# Store event
event = SpiderFootEvent("IP_ADDRESS", "1.2.3.4", "sfp_dnsresolve", root_event)
db.scanEventStore(scanId, event)

# Retrieve all events
events = db.scanResultEvent(scanId)
assert len(events) > 0

# Retrieve filtered events
ip_events = db.scanResultEvent(scanId, eventType="IP_ADDRESS")
assert all(e[0] == "IP_ADDRESS" for e in ip_events)
```

---

## Scanner Requirements

### REQ-SCAN-001: Scanner Initialization
**Description:** System SHALL initialize scanner with validated parameters
**Priority:** High
**Source:** `test/unit/test_spiderfootscanner.py:60`
**Specification:** SPEC-SCAN-001

**Requirements:**
1. SHALL require non-empty scanName (ValueError if empty)
2. SHALL require non-empty scanId (ValueError if empty)
3. SHALL require non-empty targetValue (ValueError if empty)
4. SHALL require valid targetType (event type)
5. SHALL require moduleList (list of strings)
6. SHALL require globalOpts (dict)
7. SHALL validate module names immediately
8. SHALL set status to ERROR-FAILED if invalid modules
9. SHALL create scan instance in database
10. SHALL support start=False for delayed execution

**Verification:**
```python
# Valid initialization
scanner = SpiderFootScanner(
    "Test Scan", "scan_id", "example.com", "INTERNET_NAME",
    ["sfp_dnsresolve"], {}, start=False
)

# Invalid initializations
with pytest.raises(ValueError) as e:
    SpiderFootScanner("", "id", "target", "INTERNET_NAME", [], {}, start=False)
assert "scanName value is blank" in str(e.value)

with pytest.raises(ValueError):
    SpiderFootScanner("name", "id", "", "INTERNET_NAME", [], {}, start=False)
```

**Traceability:**
- Derived from: SPEC-SCAN-001
- Tests: `test_spiderfootscanner.py`
- Design: Scanner architecture, validation logic

---

### REQ-SCAN-002: Status Management
**Description:** System SHALL manage scan status through defined state transitions
**Priority:** High
**Source:** `test/unit/test_spiderfootscanner.py:382`
**Specification:** SPEC-SCAN-002

**Requirements:**
1. SHALL maintain current status in database
2. SHALL validate status is non-empty string
3. SHALL reject invalid status types (None, int, list, etc.)
4. SHALL update started timestamp when transitioning to RUNNING
5. SHALL update ended timestamp when transitioning to FINISHED/ERROR-FAILED/ABORTED
6. SHALL follow state transition diagram:
   - INITIALIZING → ERROR-FAILED (invalid modules)
   - INITIALIZING → STARTING (validation passed)
   - STARTING → RUNNING (modules loaded)
   - RUNNING → FINISHED (completion)
   - RUNNING → ABORTED (user stopped)
   - RUNNING → ERROR-FAILED (critical error)

**Verification:**
```python
scanner = SpiderFootScanner(...)
assert scanner.status == "INITIALIZING"

# Invalid status updates
with pytest.raises(ValueError) as e:
    scanner._SpiderFootScanner__setStatus("")
assert "status value is blank" in str(e.value)

with pytest.raises(TypeError):
    scanner._SpiderFootScanner__setStatus(None)
```

---

### REQ-SCAN-003: Event Processing
**Description:** System SHALL process events through module chain
**Priority:** High
**Source:** Integration tests, acceptance tests
**Specification:** SPEC-SCAN-003

**Requirements:**
1. SHALL create ROOT event with target value
2. SHALL store ROOT event in database
3. SHALL distribute events to interested modules (watchedEvents match)
4. SHALL execute modules concurrently (up to _maxthreads)
5. SHALL store module-produced events
6. SHALL recursively process new events
7. SHALL maintain event chains (parent-child relationships)
8. SHALL continue processing until event queue empty
9. SHALL handle module exceptions gracefully
10. SHALL update scan status to FINISHED when complete

**Verification:**
- Start scan with target
- Verify ROOT event created
- Verify modules execute
- Verify new events produced and stored
- Verify event chains maintained
- Verify status updated to FINISHED

---

### REQ-SCAN-004: Resource Cleanup
**Description:** System SHALL clean up resources on scan completion
**Priority:** High
**Source:** `test/unit/test_spiderfootscanner.py`, resource leak tests

**Requirements:**
1. SHALL close database connections
2. SHALL join all worker threads (timeout: 30s)
3. SHALL NOT leak threads
4. SHALL NOT leak file handles
5. SHALL unregister event emitters
6. SHALL log warnings for abandoned threads

**Verification:**
```python
thread_count_before = threading.active_count()
scanner = SpiderFootScanner(...)
# ... scan execution ...
del scanner
thread_count_after = threading.active_count()
assert thread_count_after == thread_count_before
```

---

## Module System Requirements

### REQ-MOD-001: Module Metadata
**Description:** All modules SHALL declare required metadata
**Priority:** High
**Source:** `test/unit/test_modules.py`
**Specification:** SPEC-MOD-001

**Requirements:**
1. SHALL declare meta.name (display name)
2. SHALL declare meta.summary (description)
3. SHALL declare meta.useCases (at least one: Footprint, Passive, Investigate)
4. SHALL declare meta.categories (exactly one category, except storage modules)
5. MAY declare meta.flags (errorprone, tor, slow, invasive, apikey, tool, etc.)
6. SHALL declare meta.dataSource.model if external source (FREE_*, COMMERCIAL_*, PRIVATE_ONLY)
7. SHALL declare meta.dataSource.apiKeyInstructions if "apikey" in flags
8. SHALL declare opts dict (default option values)
9. SHALL declare optdescs dict (option descriptions)
10. SHALL ensure opts and optdescs have matching keys

**Verification:**
```python
module = sfp_example()
assert 'name' in module.meta
assert 'summary' in module.meta
assert len(module.meta['useCases']) >= 1
assert all(uc in ['Footprint', 'Passive', 'Investigate']
           for uc in module.meta['useCases'])
assert len(module.opts) == len(module.optdescs)
assert set(module.opts.keys()) == set(module.optdescs.keys())
```

---

### REQ-MOD-002: Module Lifecycle
**Description:** Modules SHALL implement required lifecycle methods
**Priority:** High
**Source:** `test/unit/modules/test_sfp_*.py`
**Specification:** SPEC-MOD-002

**Requirements:**
1. SHALL implement setup(sf, userOpts) method
2. SHALL implement watchedEvents() method returning list
3. SHALL implement producedEvents() method returning list
4. SHALL implement handleEvent(event) method
5. setup() SHALL be called before handleEvent()
6. watchedEvents() and producedEvents() SHALL be callable before setup()
7. handleEvent() SHALL NOT raise unhandled exceptions
8. Module SHALL check self.checkForStop() periodically
9. Module SHALL use self.sf for SpiderFoot operations

**Verification:**
```python
module = sfp_example()
assert hasattr(module, 'setup')
assert hasattr(module, 'watchedEvents')
assert hasattr(module, 'producedEvents')
assert hasattr(module, 'handleEvent')

watched = module.watchedEvents()
assert isinstance(watched, list)

produced = module.producedEvents()
assert isinstance(produced, list)
```

---

### REQ-MOD-003: Event Production
**Description:** Modules SHALL produce events according to specification
**Priority:** High
**Source:** Module integration tests
**Specification:** SPEC-MOD-003

**Requirements:**
1. SHALL only produce event types declared in producedEvents()
2. SHALL create SpiderFootEvent with: type, data, module, sourceEvent
3. SHALL use self.__name__ as module name
4. SHALL provide non-empty data
5. SHALL call notifyListeners() to dispatch events
6. SHALL maintain event chain by passing sourceEvent
7. SHALL NOT produce duplicate events (same hash)

**Verification:**
```python
# Module execution
module.handleEvent(input_event)

# Verify produced events
events = db.scanResultEvent(scanId)
produced_types = [e[0] for e in events]
assert all(t in module.producedEvents() for t in produced_types)
```

---

## Web UI Requirements

### REQ-UI-001: Settings Form Submission
**Description:** Web UI SHALL persist settings through form submission
**Priority:** High
**Source:** `test/regression/test_webui_settings_form_submission.py`
**Specification:** SPEC-UI-001

**Requirements:**
1. SHALL include CSRF token in form (id:token format)
2. SHALL convert JavaScript boolean strings ('true'/'false') to Python bool
3. SHALL convert numeric strings to integers
4. SHALL serialize config before database storage
5. SHALL store boolean values as "1"/"0" strings
6. SHALL redirect to /opts?updated=1 on success
7. SHALL persist settings to database (not just memory)
8. SHALL preserve settings across page reload
9. SHALL preserve settings across application restart
10. SHALL handle module-specific settings (module:option format)

**Verification:**
```python
# Submit form
response = client.post("/savesettings", data={
    'id': 'token:abc123',
    'allopts': '1',
    'sfp__stor_db:postgresql_host': 'test.host',
    'sfp__stor_db:enable_pooling': 'true'
})

# Verify redirect
assert response.status_code == 302
assert response.headers['Location'] == '/opts?updated=1'

# Verify persistence
config = db.configGet()
assert config['sfp__stor_db:postgresql_host'] == 'test.host'
assert config['sfp__stor_db:enable_pooling'] is True

# Reload page and verify
response = client.get("/opts")
assert 'test.host' in response.text
```

**Traceability:**
- Derived from: SPEC-UI-001
- Tests: `test_webui_settings_form_submission.py`, `settings_persistence.robot`
- Design: Web UI architecture, form processing
- Bug Fix: Critical regression (settings not persisting)

---

### REQ-UI-002: Scan Creation Flow
**Description:** Web UI SHALL support complete scan creation workflow
**Priority:** High
**Source:** `test/acceptance/settings_persistence.robot:66`
**Specification:** SPEC-UI-002

**Requirements:**
1. SHALL provide scan name input field (id:scanname)
2. SHALL provide scan target input field (id:scantarget)
3. SHALL provide module selection checkboxes
4. SHALL validate non-empty scan name and target
5. SHALL determine target type automatically (IP vs domain)
6. SHALL generate unique scan ID (UUID)
7. SHALL filter selected modules from checkboxes
8. SHALL start scanner in background thread
9. SHALL redirect to /scaninfo?id={scanId} immediately
10. SHALL NOT wait for scan completion before redirect

**Verification:**
```robot
Input Text    id:scanname    Test Scan
Input Text    id:scantarget    example.com
Click Button    id:btn-run-scan
Wait Until Page Contains Element    id:scan-status-badge    timeout=120s
```

---

### REQ-UI-003: Scan Information Tabs
**Description:** Web UI SHALL provide tabbed interface for scan results
**Priority:** High
**Source:** `test/acceptance/scan-firefox.robot:178`
**Specification:** SPEC-UI-003

**Requirements:**
1. SHALL provide Status tab with summary chart
2. SHALL provide Browse tab with event table, search, export
3. SHALL provide Correlations tab with correlation results
4. SHALL provide Graph tab with visualization
5. SHALL provide Info tab with scan metadata
6. SHALL provide Logs tab with log viewer
7. ALL tabs SHALL load within 120 seconds
8. Status badge SHALL reflect current scan status
9. SHALL NOT show ERROR status for valid scans
10. MAY provide real-time updates via WebSocket

**Verification:**
```robot
Click Button    id:btn-status
Wait Until Page Contains Element    id:vbarsummary    timeout=120s

Click Button    id:btn-browse
Wait Until Page Contains Element    id:search-form    timeout=120s

Click Button    id:btn-correlations
Wait Until Page Contains Element    id:correlations-table    timeout=120s
```

---

## API Requirements

### REQ-API-001: Input Sanitization
**Description:** API SHALL sanitize all user inputs to prevent XSS
**Priority:** High
**Source:** `test/unit/test_sfapi.py`
**Specification:** SPEC-API-001

**Requirements:**
1. SHALL escape HTML tags: < → &lt;, > → &gt;
2. SHALL escape ampersands: & → &amp;
3. SHALL NOT double-escape
4. SHALL preserve non-string types unchanged
5. SHALL maintain list length (1-to-1 mapping)
6. SHALL handle empty strings
7. SHALL handle Unicode characters

**Verification:**
```python
result = clean_user_input(['<script>alert("xss")</script>'])
assert result == ['&lt;script&gt;alert("xss")&lt;/script&gt;']

result = clean_user_input([123, True, None])
assert result == [123, True, None]
```

---

### REQ-API-002: Search Functionality
**Description:** API SHALL provide search endpoint for scan results
**Priority:** Medium
**Source:** `test/unit/test_sfapi_enhanced.py`
**Specification:** SPEC-API-002

**Requirements:**
1. SHALL accept scan_id parameter (optional)
2. SHALL accept value parameter (required for search)
3. SHALL accept regex parameter (format: /pattern/)
4. SHALL accept event_type parameter (optional filter)
5. SHALL return empty list if no parameters
6. SHALL return empty list if missing value parameter
7. SHALL support case-sensitive search
8. SHALL sanitize inputs to prevent SQL injection
9. SHALL return results as JSON

**Verification:**
```python
# No parameters
result = search_base(config)
assert result == []

# With value
result = search_base(config, value="example.com")
assert isinstance(result, list)

# With regex
result = search_base(config, regex="/.*\.com$/")
assert isinstance(result, list)
```

---

### REQ-API-003: WebSocket Support
**Description:** API SHALL provide WebSocket endpoint for real-time updates
**Priority:** Medium
**Source:** `test/unit/test_sfapi.py`
**Specification:** SPEC-API-003

**Requirements:**
1. SHALL manage active WebSocket connections
2. SHALL accept new connections via connect()
3. SHALL remove connections via disconnect()
4. SHALL send messages to specific clients
5. SHALL broadcast messages to all clients
6. SHALL handle disconnected clients gracefully
7. SHALL NOT crash if client disconnects mid-send

**Verification:**
```python
manager = WebSocketManager()
assert len(manager.active_connections) == 0

await manager.connect(websocket)
assert len(manager.active_connections) == 1

await manager.broadcast("test message")  # Must not crash

manager.disconnect(websocket)
assert len(manager.active_connections) == 0
```

---

## CLI Requirements

### REQ-CLI-001: Command Line Interface
**Description:** CLI SHALL provide command-line interface for all operations
**Priority:** Medium
**Source:** `test/unit/test_sfcli_enhanced.py:60`
**Specification:** SPEC-CLI-001

**Requirements:**
1. SHALL print usage if no arguments (exit 255/1/-1)
2. SHALL print help with -h/--help (exit 0)
3. SHALL list modules with -M/--modules (exit 0)
4. SHALL list event types with -T/--types (exit 0)
5. SHALL support scan operations: start, list, view, delete
6. SHALL support output formats: pretty, json, csv
7. SHALL support colored output (default: enabled)
8. SHALL support command history (default: enabled)
9. SHALL support debug mode
10. SHALL validate all inputs before processing

**Verification:**
```bash
# No args
python sf.py
# Exit code: 255/1/-1, output contains "Usage:"

# Help
python sf.py -h
# Exit code: 0, output contains help text

# List modules
python sf.py -M
# Exit code: 0, output lists 277 modules
```

---

### REQ-CLI-002: CLI Configuration
**Description:** CLI SHALL support configuration via options
**Priority:** Low
**Source:** `test/unit/test_sfcli.py`
**Specification:** SPEC-CLI-002

**Requirements:**
1. SHALL support --debug flag
2. SHALL support --silent flag
3. SHALL support --color/--no-color flags
4. SHALL support --output {pretty,json,csv}
5. SHALL support --history flag
6. SHALL support --server URL option
7. SHALL support --ssl-verify flag
8. SHALL support authentication options
9. SHALL persist history to ~/.spiderfoot_history
10. SHALL respect NO_COLOR environment variable

**Verification:**
```bash
python sf.py --output json -l
# Output in JSON format

python sf.py --no-color -l
# No ANSI color codes in output
```

---

## Non-Functional Requirements

### NFR-001: Performance - Thread Pool
**Description:** System SHALL limit concurrent threads for resource management
**Priority:** Medium
**Source:** Scanner tests, performance tests
**Specification:** SPEC-PERF-001

**Requirements:**
1. SHALL limit concurrent module threads to _maxthreads (default: 3)
2. SHALL NOT create more threads than CPU cores * 2
3. SHALL reuse threads via thread pool
4. SHALL join threads with 30s timeout on cleanup
5. SHALL NOT leak threads (verified by tests)

**Verification:**
- Configure _maxthreads=3
- Start scan
- Verify no more than 3 module threads active simultaneously
- Verify thread count returns to baseline after scan

---

### NFR-002: Performance - Timeouts
**Description:** System SHALL enforce timeouts to prevent hangs
**Priority:** High
**Source:** Multiple test files, timeout configurations
**Specification:** SPEC-PERF-002

**Requirements:**
1. SHALL timeout HTTP requests after _fetchtimeout seconds (default: 5s)
2. SHALL timeout database queries after 30 seconds
3. SHALL timeout thread joins after 30 seconds
4. SHALL timeout subprocess calls after 60 seconds
5. SHALL timeout test cases after 5 minutes
6. SHALL have global test timeout of 30 minutes
7. SHALL timeout WebUI element waits after 120 seconds
8. SHALL log timeout warnings
9. SHALL handle timeouts gracefully (no crashes)

**Verification:**
- Configure _fetchtimeout=1
- Fetch slow URL
- Verify timeout after 1 second
- Verify warning logged
- Verify no exception raised

---

### NFR-003: Security - CSRF Protection
**Description:** System SHALL protect against CSRF attacks
**Priority:** High
**Source:** Settings form tests, security tests
**Specification:** SPEC-SEC-001

**Requirements:**
1. SHALL generate cryptographically secure CSRF tokens
2. SHALL include token in all state-changing forms
3. SHALL validate token before processing requests
4. SHALL return 403 for invalid tokens
5. SHALL use constant-time comparison
6. SHALL support development mode (warn vs block)
7. GET requests SHALL NOT require CSRF tokens

**Verification:**
- Submit form without token → 403 response
- Submit form with invalid token → 403 response
- Submit form with valid token → success
- Verify constant-time comparison used

---

### NFR-004: Security - Input Validation
**Description:** System SHALL validate and sanitize all inputs
**Priority:** High
**Source:** API tests, security tests
**Specification:** SPEC-SEC-002

**Requirements:**
1. SHALL escape HTML in user inputs (prevent XSS)
2. SHALL use parameterized queries (prevent SQL injection)
3. SHALL validate file paths (prevent directory traversal)
4. SHALL validate URLs before fetching
5. SHALL limit input lengths (prevent DoS)
6. SHALL validate data types
7. SHALL reject malformed JSON/XML

**Verification:**
- Submit `<script>` in input → escaped as `&lt;script&gt;`
- Attempt SQL injection → parameterized query prevents
- Attempt path traversal `../../etc/passwd` → rejected

---

### NFR-005: Reliability - Error Handling
**Description:** System SHALL handle errors gracefully
**Priority:** High
**Source:** All test suites

**Requirements:**
1. Module exceptions SHALL NOT crash scanner
2. Network errors SHALL return None, not raise exceptions
3. File not found SHALL return None, not raise exceptions
4. Database errors SHALL log and continue
5. SHALL provide helpful error messages
6. SHALL log all errors for debugging

**Verification:**
- Module raises exception → logged, scan continues
- Network timeout → returns None, no crash
- Missing file → returns None, no crash

---

### NFR-006: Maintainability - Test Coverage
**Description:** System SHALL maintain comprehensive test coverage
**Priority:** Medium
**Source:** Test suite statistics

**Requirements:**
1. SHALL have unit tests for all core components
2. SHALL have integration tests for major workflows
3. SHALL have acceptance tests for user scenarios
4. SHALL have regression tests for fixed bugs
5. SHALL maintain test coverage > 70%
6. SHALL run tests in CI/CD pipeline

**Verification:**
- Run pytest with coverage
- Verify coverage report > 70%
- Verify all critical paths tested

---

## Requirements Traceability Matrix

### Core Library Traceability

| Requirement | Specification | Test File | Design Doc | Priority |
|-------------|---------------|-----------|------------|----------|
| REQ-CORE-001 | SPEC-CORE-001 | test_spiderfoot.py:35 | 01-system-architecture.md | High |
| REQ-CORE-002 | SPEC-CORE-002 | test_sflib.py:123 | 01-system-architecture.md | Medium |
| REQ-CORE-003 | SPEC-CORE-003 | test_sflib.py:173 | 01-system-architecture.md | High |
| REQ-CORE-004 | SPEC-CORE-004 | test_sflib.py:297 | 01-system-architecture.md | Medium |
| REQ-CORE-005 | SPEC-CORE-005 | test_spiderfoot.py | 01-system-architecture.md | High |
| REQ-CORE-006 | - | test_sflib.py | 01-system-architecture.md | High |

### Database Traceability

| Requirement | Specification | Test File | Design Doc | Priority |
|-------------|---------------|-----------|------------|----------|
| REQ-DB-001 | SPEC-DB-001 | test_spiderfootdb.py:35 | 01-system-architecture.md | High |
| REQ-DB-002 | SPEC-DB-002 | test_spiderfootdb.py | 01-system-architecture.md | High |
| REQ-DB-003 | SPEC-DB-003 | test_database_settings_persistence.py | 01-system-architecture.md | High |
| REQ-DB-004 | SPEC-DB-004 | test_spiderfootdb.py | 01-system-architecture.md | High |
| REQ-DB-005 | SPEC-DB-005 | test_spiderfootdb.py | 01-system-architecture.md | High |

### Scanner Traceability

| Requirement | Specification | Test File | Design Doc | Priority |
|-------------|---------------|-----------|------------|----------|
| REQ-SCAN-001 | SPEC-SCAN-001 | test_spiderfootscanner.py:60 | 01-system-architecture.md | High |
| REQ-SCAN-002 | SPEC-SCAN-002 | test_spiderfootscanner.py:382 | 01-system-architecture.md | High |
| REQ-SCAN-003 | SPEC-SCAN-003 | Integration tests | 01-system-architecture.md | High |
| REQ-SCAN-004 | - | Resource leak tests | 01-system-architecture.md | High |

### Module System Traceability

| Requirement | Specification | Test File | Design Doc | Priority |
|-------------|---------------|-----------|------------|----------|
| REQ-MOD-001 | SPEC-MOD-001 | test_modules.py | 01-system-architecture.md | High |
| REQ-MOD-002 | SPEC-MOD-002 | test_sfp_*.py (272 files) | 01-system-architecture.md | High |
| REQ-MOD-003 | SPEC-MOD-003 | Module integration tests | 01-system-architecture.md | High |

### Web UI Traceability

| Requirement | Specification | Test File | Design Doc | Priority |
|-------------|---------------|-----------|------------|----------|
| REQ-UI-001 | SPEC-UI-001 | test_webui_settings_form_submission.py | 01-system-architecture.md | High |
| REQ-UI-002 | SPEC-UI-002 | settings_persistence.robot:66 | 01-system-architecture.md | High |
| REQ-UI-003 | SPEC-UI-003 | scan-firefox.robot:178 | 01-system-architecture.md | High |

### API Traceability

| Requirement | Specification | Test File | Design Doc | Priority |
|-------------|---------------|-----------|------------|----------|
| REQ-API-001 | SPEC-API-001 | test_sfapi.py | 01-system-architecture.md | High |
| REQ-API-002 | SPEC-API-002 | test_sfapi_enhanced.py | 01-system-architecture.md | Medium |
| REQ-API-003 | SPEC-API-003 | test_sfapi.py | 01-system-architecture.md | Medium |

### CLI Traceability

| Requirement | Specification | Test File | Design Doc | Priority |
|-------------|---------------|-----------|------------|----------|
| REQ-CLI-001 | SPEC-CLI-001 | test_sfcli_enhanced.py:60 | 01-system-architecture.md | Medium |
| REQ-CLI-002 | SPEC-CLI-002 | test_sfcli.py | 01-system-architecture.md | Low |

### Non-Functional Traceability

| Requirement | Specification | Test File | Design Doc | Priority |
|-------------|---------------|-----------|------------|----------|
| NFR-001 | SPEC-PERF-001 | Scanner tests | 01-system-architecture.md | Medium |
| NFR-002 | SPEC-PERF-002 | Multiple test files | 01-system-architecture.md | High |
| NFR-003 | SPEC-SEC-001 | Settings tests | 01-system-architecture.md | High |
| NFR-004 | SPEC-SEC-002 | API tests | 01-system-architecture.md | High |
| NFR-005 | - | All test suites | 01-system-architecture.md | High |
| NFR-006 | - | Test statistics | 01-system-architecture.md | Medium |

---

## Summary Statistics

- **Total User Requirements:** 6
- **Total System Requirements:** 5
- **Total Functional Requirements:** 30+
- **Total Non-Functional Requirements:** 6
- **Total Requirements:** 47+
- **Test Coverage:** 590 test files, ~55,177 lines
- **Verification Method:** Executable tests
- **Traceability:** Tests → Specs → Requirements → Design

---

## Verification Strategy

### Test-Driven Verification
All requirements are verified through existing test suite:
- **Unit Tests:** Component-level verification
- **Integration Tests:** Cross-component verification
- **Acceptance Tests:** User scenario verification
- **Regression Tests:** Bug fix verification

### Traceability Chain
```
User Need → User Requirement → System Requirement →
Functional Requirement → Specification → Test → Implementation
```

### Coverage Metrics
- Unit test coverage: 683 test functions
- Integration test coverage: 244 test files
- Acceptance scenarios: 4 Robot files
- Regression scenarios: 3 test files
- Total test lines: ~55,177

---

This requirements document provides complete traceability from user needs through specifications to executable tests, enabling verification that the system meets all documented requirements.
