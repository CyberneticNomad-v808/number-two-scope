# SpiderFoot Integration Tests Analysis

## Summary

Out of ~200 integration test files for SpiderFoot modules:
- **75 tests** have real implementations (ready to run)
- **125 tests** are stubs marked with `@unittest.skip("todo")`

## Test Categories

### ✅ Pure Mock Tests (26 tests)
These tests use only mocks and don't require external dependencies:

- `_stor_stdout` - Standard output storage module
- `adguard_dns` - AdGuard DNS module
- `alienvaultiprep` - AlienVault IP reputation
- `bambenek` - Bambenek feeds
- `binaryedge` - BinaryEdge integration
- `cleanbrowsing` - CleanBrowsing DNS
- `cleantalk` - CleanTalk anti-spam
- `cloudflaredns` - Cloudflare DNS
- `comodo` - Comodo Secure DNS
- `dns_for_family` - DNS for Family
- `dnsresolve` - DNS resolution
- `douyin` - Douyin (TikTok China)
- `dronebl` - DroneBL RBL
- `opendns` - OpenDNS
- `opennic` - OpenNIC DNS
- `quad9` - Quad9 DNS
- `sorbs` - SORBS RBL
- `spamcop` - SpamCop RBL
- `spamhaus` - Spamhaus RBL
- `surbl` - SURBL
- `tool_nuclei` - Nuclei scanner tool
- `uceprotect` - UCEPROTECT RBL
- `wechat` - WeChat integration
- `xiaohongshu` - Xiaohongshu (Little Red Book)
- `yandexdns` - Yandex DNS
- `zoomeye` - ZoomEye search

### 🗄️ Database Required (5 tests)
These tests require PostgreSQL database:

- `_stor_db` - Database storage module
- `_stor_elasticsearch` - Elasticsearch storage
- `abstractapi` - AbstractAPI integration
- `cisco_umbrella` - Cisco Umbrella
- `rocketreach` - RocketReach API

### 🌐 Network Mocking (42 tests)
These tests mock HTTP/network requests:

- `4chan` - 4chan scraping
- `accounts` - Account enumeration
- `adblock` - Adblock lists
- `alienvault` - AlienVault OTX
- `aparat` - Aparat video
- `apple_itunes` - Apple iTunes
- `archiveorg` - Internet Archive
- `arin` - ARIN WHOIS
- `blockchain` - Blockchain.info
- `botscout` - BotScout
- `botvrij` - Botvrij RBL
- `builtwith` - BuiltWith
- `c99` - C99.nl API
- `callername` - Caller Name
- `censys` - Censys
- `certspotter` - Cert Spotter
- `cinsscore` - CINS Score
- `circllu` - Circllu
- `citadel` - Citadel RBL
- `cloudfront` - CloudFront
- `criminalip` - Criminal IP
- `discord` - Discord
- `fofa` - FOFA
- `hosting` - Hosting provider detection
- `instagram` - Instagram
- `leakcheck` - LeakCheck
- `luminar` - Luminar
- `mandiant_ti` - Mandiant Threat Intelligence
- `netlas` - Netlas
- `neutrinoapi` - NeutrinoAPI
- `numverify` - Numverify
- `onioncity` - Onion.City
- `onionsearchengine` - Onion Search Engine
- `onyphe` - ONYPHE
- `recordedfuture` - Recorded Future
- `stevenblack_hosts` - Steven Black's hosts
- `tool_phoneinfoga` - PhoneInfoga tool
- `tool_wappalyzer` - Wappalyzer tool
- `twitter` - Twitter
- `urlscan` - URLScan.io
- `virustotal` - VirusTotal
- `whoisfreaks` - WhoisFreaks

### 📦 External Dependencies (2 tests)
These import `requests` library directly:

- `abusech` - Abuse.ch feeds
- `abuseipdb` - AbuseIPDB

## Running the Tests

### Quick Start

```bash
# Run all 75 implemented tests with 8 parallel workers
./run_implemented_integration_tests.sh

# Run with 16 workers
./run_implemented_integration_tests.sh -n 16

# Run with verbose output
./run_implemented_integration_tests.sh -v

# Stop on first failure
./run_implemented_integration_tests.sh -x

# Custom timeout (60 seconds per test)
./run_implemented_integration_tests.sh -t 60
```

### Manual Run

```bash
# Activate test environment
source test/venv/bin/activate

# Run with op (1Password) for environment variables
op run --env-file='./test/.env.test' -- pytest \
    -n 8 \
    --timeout=30 \
    --tb=short \
    $(cat runnable_integration_tests.txt)
```

### Run Specific Category

```bash
# Only pure mock tests (fastest, no database needed)
op run --env-file='./test/.env.test' -- pytest \
    -n 8 \
    test/integration/modules/test_sfp_{_stor_stdout,adguard_dns,bambenek,cleanbrowsing}.py

# Only database tests
op run --env-file='./test/.env.test' -- pytest \
    -n 4 \
    test/integration/modules/test_sfp_{_stor_db,_stor_elasticsearch,abstractapi}.py
```

## Requirements

### All Tests
- Python 3.12+
- PostgreSQL test database
- Test environment variables in `test/.env.test`
- pytest, pytest-xdist, pytest-timeout, pytest-mock

### Database Tests (5 tests)
- PostgreSQL container `unified-postgres` running
- Database `spiderfoot_test` created
- User `spiderfoot_test` with CREATE permissions

### External Dependency Tests (2 tests)
- `requests` library (already installed)

## Test File Structure

Each test file follows this pattern:

```python
import unittest
from test.unit.utils.test_module_base import TestModuleBase
from unittest.mock import patch
from modules.sfp_<module> import sfp_<module>
from spiderfoot import SpiderFootEvent, SpiderFootTarget

class TestModuleIntegration<Module>(TestModuleBase):
    def setUp(self):
        # Setup test environment
        
    @patch('modules.sfp_<module>.<external_call>')
    def test_<scenario>(self, mock_call):
        # Test specific scenario
```

## Skipped Tests (125 tests)

These are marked with `@unittest.skip("todo")` and are not implemented yet:
- They have basic structure but no actual test logic
- All are exactly 44 lines long
- Examples: `torch`, `shodan`, `greynoise`, `github`, `whois`, etc.

## Troubleshooting

### Database Permission Errors
```bash
# Grant CREATE permission to test user
docker exec unified-postgres psql -U postgres -d spiderfoot_test \
    -c "GRANT CREATE ON SCHEMA public TO spiderfoot_test;"
```

### Tests Hanging
- Use `--timeout=30` flag (already in pytest.ini)
- Reduce parallel workers: `-n 4` instead of `-n 8`

### Worker Crashes
- Check database connection pool limits
- Run sequentially: `-n 0` to disable parallelization

## Analysis Script

Use `analyze_tests.py` to regenerate the test categorization:

```bash
python3 analyze_tests.py
```

This will:
1. Scan all test files in `test/integration/modules/`
2. Categorize by requirements
3. Generate `runnable_integration_tests.txt`
4. Print summary report

## Contributing

To convert a "todo" test to an implemented test:

1. Remove the `@unittest.skip("todo")` decorator
2. Add proper mocking with `@patch` decorators
3. Implement test logic with assertions
4. Add multiple test scenarios (success, failure, edge cases)
5. Run `python3 analyze_tests.py` to update the runnable list
