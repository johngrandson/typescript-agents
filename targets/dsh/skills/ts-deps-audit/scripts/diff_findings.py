#!/usr/bin/env python3
"""Compare exact native fingerprints while preserving original severities."""
import argparse
from pathlib import Path
from audit_core import atomic_json, read_json


def compare(old, new):
    before = {f['fingerprint'] for f in old}
    after = {f['fingerprint'] for f in new}
    return [dict(f, differential='carried' if f['fingerprint'] in before else 'new') for f in new] + [dict(f, differential='dropped') for f in old if f['fingerprint'] not in after]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old', type=Path)
    parser.add_argument('new', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    atomic_json(args.output, compare(read_json(args.old)['findings'], read_json(args.new)['findings']))


if __name__ == '__main__':
    main()
