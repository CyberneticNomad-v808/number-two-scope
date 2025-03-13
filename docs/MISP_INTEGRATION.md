# SpiderFoot MISP Integration

This document explains how to use the MISP (Malware Information Sharing Platform) integration in SpiderFoot.

## Overview

The MISP integration allows you to:

1. Export SpiderFoot scan results to MISP-compatible format
2. Directly publish results to a MISP instance
3. Use MISP taxonomies for classifying data
4. Create structured MISP objects from SpiderFoot data

## Requirements

To use the MISP integration, you need:

- SpiderFoot (latest version)
- Optional: `pymisp` Python package for direct publishing to MISP instances

```bash
pip install pymisp
```

## Usage

### Using the MISP Module

SpiderFoot includes a `sfp_misp` module that enables MISP integration during scans:

1. Enable the module in the SpiderFoot UI or with the command line interface
2. Configure the module options:
   - `misp_url`: URL of your MISP instance (if publishing directly)
   - `misp_key`: API key for your MISP instance (if publishing directly)
   - `create_misp_event`: Whether to create a MISP event from scan results
   - `create_misp_objects`: Whether to create structured MISP objects
   - `tag_tlp`: TLP tag to apply (e.g., `tlp:amber`)
   - `confidence_threshold`: Minimum confidence for including events (0-100)
   - `enable_auto_publishing`: Whether to automatically publish to MISP

### Using the Command Line Tool

SpiderFoot includes a command line tool (`sfmisp.py`) for exporting scan results to MISP format:

```bash
python tools/sfmisp.py -s SCAN_ID -o output.json
```

Options:
- `-s, --scan-id`: SpiderFoot scan ID (required)
- `-d, --db-path`: Path to SpiderFoot database (default: ~/.spiderfoot/spiderfoot.db)
- `-o, --output`: Output file (defaults to stdout)
- `-p, --publish`: Publish directly to MISP
- `-u, --misp-url`: MISP URL (required if publishing)
- `-k, --misp-key`: MISP API key (required if publishing)
- `-t, --tlp`: TLP tag (default: tlp:amber)
- `-c, --confidence-threshold`: Minimum confidence score (0-100)

Example for publishing directly to MISP:

```bash
python tools/sfmisp.py -s SCAN_ID -p -u https://misp.example.com -k YOUR_API_KEY
```

## MISP Object Types

The integration supports creating various MISP object types from SpiderFoot data:

- Domain-IP: Links domains to IP addresses
- URL: Structured URL information
- SSL Certificate: Certificate information
- Person: Combines names, emails, and phone numbers
- Vulnerability: CVE and vulnerability details

## Taxonomies

The integration supports MISP taxonomies for classification:

- TLP (Traffic Light Protocol): Information sharing restrictions
- Confidence: Level of confidence in the data
- Threat Actor: Classification of threat actors

## Programmatic Usage

You can use the MISP integration programmatically in your own scripts:

```python
from spiderfoot import SpiderFootDb
from spiderfoot.misp_integration import MispIntegration

# Initialize database and MISP integration
db = SpiderFootDb({'__database': 'spiderfoot.db'})
misp = MispIntegration(db)

# Create MISP event from scan
event = misp.create_misp_event_from_scan('YOUR_SCAN_ID')

# Export as JSON
misp_json = misp.export_misp_event(event, 'json')
print(misp_json)
```
