#!/usr/bin/env python3
"""Analyze integration test requirements."""

import os
import re
from pathlib import Path
from collections import defaultdict

def analyze_test_file(filepath):
    """Analyze a single test file for requirements."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    analysis = {
        'file': filepath.name,
        'module': filepath.stem.replace('test_sfp_', ''),
        'imports': [],
        'patches': [],
        'external_deps': [],
        'has_db': False,
        'has_network': False,
        'has_skip': False,
        'line_count': len(content.split('\n'))
    }
    
    # Check for imports
    for match in re.finditer(r'^(?:from|import)\s+(\S+)', content, re.MULTILINE):
        imp = match.group(1)
        analysis['imports'].append(imp)
        
        # Check for external dependencies
        if imp in ['requests', 'elasticsearch', 'psycopg2', 'redis']:
            analysis['external_deps'].append(imp)
    
    # Check for patches
    for match in re.finditer(r'@patch\([\'"]([^\'"]+)', content):
        analysis['patches'].append(match.group(1))
    
    # Check for database usage
    if 'dbh' in content or 'database' in content.lower() or 'SpiderFootDb' in content:
        analysis['has_db'] = True
    
    # Check for network mocking
    if 'requests.' in content or 'fetchUrl' in content or 'http' in content.lower():
        analysis['has_network'] = True
    
    # Check for skip decorators
    if '@unittest.skip' in content or 'pytest.skip' in content:
        analysis['has_skip'] = True
    
    return analysis

def main():
    test_dir = Path('/stuff/spiderfoot/test/integration/modules')
    
    # Find all test files with >44 lines (implemented tests)
    test_files = []
    for f in sorted(test_dir.glob('test_sfp_*.py')):
        line_count = len(f.read_text().split('\n'))
        if line_count > 44:
            test_files.append(f)
    
    print(f"Found {len(test_files)} implemented test files\n")
    
    # Analyze all tests
    analyses = []
    for test_file in test_files:
        analysis = analyze_test_file(test_file)
        analyses.append(analysis)
    
    # Categorize
    categories = {
        'pure_mock': [],
        'needs_db': [],
        'needs_network': [],
        'has_external_deps': [],
        'skipped': []
    }
    
    for analysis in analyses:
        if analysis['has_skip']:
            categories['skipped'].append(analysis['module'])
        elif analysis['external_deps']:
            categories['has_external_deps'].append(analysis['module'])
        elif analysis['has_db']:
            categories['needs_db'].append(analysis['module'])
        elif analysis['has_network']:
            categories['needs_network'].append(analysis['module'])
        else:
            categories['pure_mock'].append(analysis['module'])
    
    # Print summary
    print("=" * 70)
    print("TEST REQUIREMENTS SUMMARY")
    print("=" * 70)
    
    print(f"\n✅ Pure Mock Tests (no external deps): {len(categories['pure_mock'])}")
    for mod in sorted(categories['pure_mock']):
        print(f"   - {mod}")
    
    print(f"\n🗄️  Database Required: {len(categories['needs_db'])}")
    for mod in sorted(categories['needs_db']):
        print(f"   - {mod}")
    
    print(f"\n🌐 Network Mocking: {len(categories['needs_network'])}")
    for mod in sorted(categories['needs_network'])[:10]:
        print(f"   - {mod}")
    if len(categories['needs_network']) > 10:
        print(f"   ... and {len(categories['needs_network']) - 10} more")
    
    print(f"\n📦 External Dependencies: {len(categories['has_external_deps'])}")
    for mod in sorted(categories['has_external_deps']):
        print(f"   - {mod}")
    
    print(f"\n⏭️  Skipped Tests: {len(categories['skipped'])}")
    for mod in sorted(categories['skipped']):
        print(f"   - {mod}")
    
    # Dependency summary
    print("\n" + "=" * 70)
    print("EXTERNAL DEPENDENCIES USED")
    print("=" * 70)
    
    dep_count = defaultdict(int)
    for analysis in analyses:
        for dep in analysis['external_deps']:
            dep_count[dep] += 1
    
    for dep, count in sorted(dep_count.items(), key=lambda x: -x[1]):
        print(f"  {dep}: {count} tests")
    
    # Generate test list for runner
    runnable_tests = []
    for analysis in analyses:
        if not analysis['has_skip']:
            runnable_tests.append(f"test/integration/modules/{analysis['file']}")
    
    print("\n" + "=" * 70)
    print(f"RUNNABLE TESTS: {len(runnable_tests)}")
    print("=" * 70)
    
    # Save to file
    output_file = Path('/stuff/spiderfoot/runnable_integration_tests.txt')
    output_file.write_text('\n'.join(runnable_tests))
    print(f"\n✅ Saved runnable test list to: {output_file}")

if __name__ == '__main__':
    main()
