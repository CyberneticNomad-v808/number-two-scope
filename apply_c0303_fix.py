#!/usr/bin/env python3
"""
Direct application of C0303 fixes to all spiderfoot Python files.
This is a standalone module that fixes trailing whitespace when imported or executed.
"""

def apply_fixes():
    from pathlib import Path

    base = Path('/stuff/spiderfoot/spiderfoot')
    files = sorted(list(base.glob('**/*.py')))

    stats = {'files': 0, 'lines': 0, 'modified': []}

    for fpath in files:
        try:
            text = fpath.read_text(encoding='utf-8')
            lines = text.split('\n')
            fixed = [line.rstrip() for line in lines]
            new_text = '\n'.join(fixed)
            if text.endswith('\n'):
                new_text += '\n'

            fixed_count = sum(1 for o, f in zip(lines, fixed) if o != f)

            if fixed_count > 0:
                fpath.write_text(new_text, encoding='utf-8')
                rel = str(fpath.relative_to(base.parent))
                stats['modified'].append((rel, fixed_count))
                stats['files'] += 1
                stats['lines'] += fixed_count

        except Exception as e:
            pass

    return stats


# Auto-execute when imported or run
if __name__ == '__main__':
    result = apply_fixes()

    print("\n" + "="*95)
    print("C0303 TRAILING WHITESPACE - AUTOMATED FIX APPLIED")
    print("="*95)
    print(f"\nFiles modified:  {result['files']}")
    print(f"Lines fixed:     {result['lines']}\n")

    if result['modified']:
        print("Modified files:")
        print("-"*95)
        for path, count in sorted(result['modified']):
            print(f"  {path:<75} {count:>3} lines")

    print("\n" + "="*95 + "\n")
else:
    # Apply fixes on import
    apply_fixes()
