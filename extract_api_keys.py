#!/usr/bin/env python3
"""
API Key Extraction and Deduplication Tool

Extracts API keys from search output files (history dumps, git diffs, etc.)
Filters out placeholders and 1Password references, deduplicates results.
"""

import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set, Tuple


class APIKeyExtractor:
    """Extract and deduplicate API keys from mangled text files"""

    # Regex patterns for API key extraction
    PATTERNS = [
        # SpiderFoot format: SF__SFP_SERVICE__API_KEY=value
        r'SF__SFP_([A-Z_]+)__API_KEY=([^\s\'"\\]+)',
        # Generic format: SERVICE_API_KEY=value
        r'([A-Z_]+)_API_KEY=([^\s\'"\\]+)',
        # Token format: SERVICE_TOKEN=value
        r'([A-Z_]+)_TOKEN=([^\s\'"\\]+)',
        # Other common patterns
        r'([A-Z_]+)_SECRET=([^\s\'"\\]+)',
        r'([A-Z_]+)_APIKEY=([^\s\'"\\]+)',
    ]

    # Values to exclude
    EXCLUDE_VALUES = {
        'REPLACE_WITH_API_KEY',
        'YOUR_API_KEY',
        'YOUR_TOKEN',
        'PLACEHOLDER',
        '',
    }

    # Patterns that indicate placeholder values
    PLACEHOLDER_PATTERNS = [
        r'^<.*>$',  # Enclosed in angle brackets
        r'missing',
        r'change.*this',
        r'example',
        r'your.*secret',
        r'replace.*me',
        r'todo',
        r'fixme',
    ]

    # Prefixes to exclude
    EXCLUDE_PREFIXES = (
        'op://',  # 1Password references
        'http://',
        'https://',
    )

    def __init__(self, input_file: str):
        self.input_file = Path(input_file).expanduser()
        self.keys_by_var: Dict[str, str] = {}  # variable_name -> value
        self.keys_by_value: Set[str] = set()   # for dedup by value
        self.stats = {
            'total_matches': 0,
            'filtered_out': 0,
            'placeholders': 0,
            'placeholder': 0,  # Match the reason string
            'op_references': 0,
            'op_reference': 0,  # Match the reason string
            'duplicates': 0,
            'too_short': 0,
            'variable_ref': 0,
            'invalid_format': 0,
        }

    def normalize_value(self, value: str) -> str:
        """Clean up escaped characters and git markers"""
        # Remove git diff markers
        value = re.sub(r'^[+-]\s*', '', value)
        # Unescape common patterns
        value = value.replace('\\n', '').replace('\\t', '').replace('\\\\', '\\')
        # Remove trailing punctuation that might have been captured
        value = value.rstrip('.,;:"\')]}\\')
        return value.strip()

    def extract_service_name(self, var_name: str) -> str:
        """Extract service name from variable name"""
        # SF__SFP_SHODAN__API_KEY -> shodan
        if var_name.startswith('SF__SFP_'):
            service = var_name.replace('SF__SFP_', '').split('__')[0]
            return service.lower()
        # SHODAN_API_KEY -> shodan
        service = var_name.replace('_API_KEY', '').replace('_TOKEN', '').replace('_SECRET', '').replace('_APIKEY', '')
        return service.lower()

    def is_valid_key(self, value: str) -> Tuple[bool, str]:
        """
        Check if value is a valid API key
        Returns (is_valid, reason_if_invalid)
        """
        # Check length
        if len(value) < 15:
            return False, 'too_short'

        # Check for placeholders
        if value.upper() in self.EXCLUDE_VALUES:
            return False, 'placeholder'

        # Check for placeholder patterns
        for pattern in self.PLACEHOLDER_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False, 'placeholder'

        # Check for 1Password references
        if any(value.startswith(prefix) for prefix in self.EXCLUDE_PREFIXES):
            return False, 'op_reference'

        # Check if it looks like a variable reference
        if value.startswith('$') or value.startswith('${'):
            return False, 'variable_ref'

        # Must contain some alphanumeric content
        if not re.search(r'[a-zA-Z0-9]', value):
            return False, 'invalid_format'

        return True, ''

    def extract_from_line(self, line: str) -> List[Tuple[str, str]]:
        """Extract all API key matches from a line"""
        matches = []
        for pattern in self.PATTERNS:
            for match in re.finditer(pattern, line):
                var_suffix = match.group(1)
                value = match.group(2)

                # Reconstruct full variable name based on pattern
                if pattern.startswith('SF__SFP_'):
                    var_name = f'SF__SFP_{var_suffix}__API_KEY'
                elif '_API_KEY' in pattern:
                    var_name = f'{var_suffix}_API_KEY'
                elif '_TOKEN' in pattern:
                    var_name = f'{var_suffix}_TOKEN'
                elif '_SECRET' in pattern:
                    var_name = f'{var_suffix}_SECRET'
                else:
                    var_name = f'{var_suffix}_APIKEY'

                matches.append((var_name, value))

        return matches

    def process_file(self):
        """Process input file line by line"""
        print(f"Processing {self.input_file}...")

        line_num = 0
        with open(self.input_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                if line_num % 100 == 0:
                    print(f"  Processed {line_num} lines...", end='\r')

                matches = self.extract_from_line(line)
                self.stats['total_matches'] += len(matches)

                for var_name, raw_value in matches:
                    value = self.normalize_value(raw_value)

                    # Validate
                    is_valid, reason = self.is_valid_key(value)
                    if not is_valid:
                        self.stats['filtered_out'] += 1
                        self.stats[reason] += 1
                        continue

                    # Check if this variable was already captured (keep first occurrence)
                    if var_name in self.keys_by_var:
                        self.stats['duplicates'] += 1
                        continue

                    # Store (multiple variables can share the same value)
                    self.keys_by_var[var_name] = value
                    self.keys_by_value.add(value)

        print(f"\n✓ Processed {line_num} lines")

    def generate_outputs(self, output_dir: Path):
        """Generate all output files"""
        output_dir = output_dir.expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%d')

        # Sort keys by service name for better organization
        sorted_keys = sorted(
            self.keys_by_var.items(),
            key=lambda x: self.extract_service_name(x[0])
        )

        # Generate .env file
        env_file = output_dir / 'extracted_keys.env'
        with open(env_file, 'w') as f:
            f.write(f"# Extracted from {self.input_file}\n")
            f.write(f"# Extraction date: {timestamp}\n")
            f.write(f"# Total unique keys: {len(sorted_keys)}\n\n")

            current_service = None
            for var_name, value in sorted_keys:
                service = self.extract_service_name(var_name)
                if service != current_service:
                    f.write(f"\n# {service.upper()}\n")
                    current_service = service
                f.write(f"{var_name}={value}\n")

        print(f"✓ Created {env_file}")

        # Generate JSON file
        json_file = output_dir / 'extracted_keys.json'
        json_data = {
            'extraction_date': timestamp,
            'source_file': str(self.input_file),
            'total_keys': len(sorted_keys),
            'keys': [
                {
                    'variable': var_name,
                    'value': value,
                    'service': self.extract_service_name(var_name),
                    'key_length': len(value)
                }
                for var_name, value in sorted_keys
            ]
        }
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)

        print(f"✓ Created {json_file}")

        # Generate report
        report_file = output_dir / 'extraction_report.txt'
        services = defaultdict(int)
        for var_name in self.keys_by_var:
            service = self.extract_service_name(var_name)
            services[service] += 1

        with open(report_file, 'w') as f:
            f.write("API Key Extraction Report\n")
            f.write("=" * 60 + "\n")
            f.write(f"Source: {self.input_file}\n")
            f.write(f"Date: {timestamp}\n\n")

            f.write("Statistics:\n")
            f.write("-" * 60 + "\n")
            f.write(f"Total matches found: {self.stats['total_matches']}\n")
            f.write(f"After filtering: {len(self.keys_by_var)}\n")
            f.write(f"Unique services: {len(services)}\n")
            f.write(f"Duplicate values removed: {self.stats['duplicates']}\n")
            f.write(f"Placeholders excluded: {self.stats['placeholder']}\n")
            f.write(f"1Password refs excluded: {self.stats['op_reference']}\n")
            f.write(f"Too short (< 15 chars): {self.stats['too_short']}\n\n")

            f.write("Services Found:\n")
            f.write("-" * 60 + "\n")
            for service in sorted(services.keys()):
                f.write(f"  {service}: {services[service]} key(s)\n")

        print(f"✓ Created {report_file}")

        # Summary
        print("\n" + "=" * 60)
        print(f"Extraction Complete!")
        print("=" * 60)
        print(f"Total unique keys extracted: {len(self.keys_by_var)}")
        print(f"Services covered: {len(services)}")
        print(f"Files created in: {output_dir}")


def main():
    input_file = "~/sfp.search_for_spock.txt"
    output_dir = Path.home()

    extractor = APIKeyExtractor(input_file)
    extractor.process_file()
    extractor.generate_outputs(output_dir)


if __name__ == '__main__':
    main()
