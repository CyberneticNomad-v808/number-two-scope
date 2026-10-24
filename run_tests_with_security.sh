#!/bin/bash
set -e

echo "=== SpiderFoot Comprehensive Test & Security Scan ==="
echo "Starting at: $(date)"

# Verify required env vars are set
: "${SPIDERFOOT_DB_TYPE:?SPIDERFOOT_DB_TYPE must be set}"
: "${SPIDERFOOT_DB_HOST:?SPIDERFOOT_DB_HOST must be set}"
: "${SPIDERFOOT_DB_NAME:?SPIDERFOOT_DB_NAME must be set}"
: "${SPIDERFOOT_DB_USER:?SPIDERFOOT_DB_USER must be set}"
: "${SPIDERFOOT_DB_PASSWORD:?SPIDERFOOT_DB_PASSWORD must be set}"
: "${SONAR_TOKEN:?SONAR_TOKEN must be set}"

# Install required tools if not present
echo "=== Checking/Installing Security Tools ==="
pip install bandit safety pytest-cov pytest-xdist

# Clean previous reports
echo "=== Cleaning Previous Reports ==="
rm -rf htmlcov/ .coverage coverage.xml test-results.xml bandit-report.json safety-report.json

# Run tests with coverage
echo "=== Running Tests with Coverage (16 parallel workers) ==="
pytest --junitxml=test-results.xml

# Run Bandit security scan
echo "=== Running Bandit Security Scan ==="
bandit -r spiderfoot/ modules/ -f json -o bandit-report.json
bandit -r spiderfoot/ modules/ -f txt

# Run Safety vulnerability check
echo "=== Running Safety Vulnerability Check ==="
safety check --json > safety-report.json
safety check

# Display coverage summary
echo "=== Coverage Summary ==="
[ -f coverage.xml ] && echo "Coverage report generated: coverage.xml"
[ -d htmlcov ] && echo "HTML coverage report: htmlcov/index.html"

# Upload to SonarQube
echo "=== Uploading to SonarQube ==="
sonar-scanner

echo ""
echo "=== Test & Security Scan Complete ==="
echo "Finished at: $(date)"
echo ""
echo "Reports generated:"
echo "  - Test results: test-results.xml"
echo "  - Coverage XML: coverage.xml"
echo "  - Coverage HTML: htmlcov/index.html"
echo "  - Bandit security: bandit-report.json"
echo "  - Safety vulnerabilities: safety-report.json"
echo "  - SonarQube: https://sonar.blk.ing/dashboard?id=blkc-spiderfoot"
