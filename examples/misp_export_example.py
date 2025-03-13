#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example script demonstrating how to export SpiderFoot scan results to MISP format
"""

import sys
import json
import argparse
from pathlib import Path

# Add SpiderFoot directory to path
script_dir = Path(__file__).resolve().parent
spiderfoot_dir = script_dir.parent
sys.path.insert(0, str(spiderfoot_dir))

from spiderfoot import SpiderFootDb
from spiderfoot.misp_integration import MispIntegration


def parse_args():
    parser = argparse.ArgumentParser(description="Export SpiderFoot scan to MISP format")
    parser.add_argument("-d", "--database", help="SpiderFoot database path", 
                        default=str(Path.home() / '.spiderfoot' / 'spiderfoot.db'))
    parser.add_argument("-s", "--scan-id", help="Scan ID to export", required=True)
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("-t", "--tag", help="TLP tag (default: tlp:amber)", default="tlp:amber")
    return parser.parse_args()


def main():
    args = parse_args()
    
    print(f"Connecting to database: {args.database}")
    db = SpiderFootDb({"__database": args.database})
    
    # Check if scan exists
    scan_info = db.scanInstanceGet(args.scan_id)
    if not scan_info:
        print(f"Error: Scan with ID {args.scan_id} not found")
        return 1
        
    print(f"Found scan: {scan_info[0]}")
    
    # Initialize MISP integration
    misp = MispIntegration(db)
    
    # Create MISP event from scan
    print("Creating MISP event from scan results...")
    event = misp.create_misp_event_from_scan(args.scan_id)
    
    # Add TLP tag
    if args.tag:
        event.add_tag(args.tag)
        
    # Export to JSON
    misp_json = misp.export_misp_event(event, "json")
    
    # Write to file or stdout
    if args.output:
        with open(args.output, 'w') as f:
            f.write(misp_json)
        print(f"MISP event written to {args.output}")
    else:
        print(misp_json)
        
    print(f"Event contains {len(event.attributes)} attributes and {len(event.objects)} objects")
    
    # Print object types summary
    obj_types = {}
    for obj in event.objects:
        if obj.name not in obj_types:
            obj_types[obj.name] = 0
        obj_types[obj.name] += 1
        
    print("\nObject types summary:")
    for obj_type, count in obj_types.items():
        print(f"  {obj_type}: {count}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
