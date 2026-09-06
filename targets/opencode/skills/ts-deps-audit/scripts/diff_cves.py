#!/usr/bin/env python3
"""Compare normalized advisory exposures and graph occurrences as JSON."""
import argparse
from pathlib import Path
from audit_core import atomic_json, read_json
from analysis import advisory_diff


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old', type=Path, help='JSON with exposures and graph')
    parser.add_argument('new', type=Path, help='JSON with exposures and graph')
    parser.add_argument('output', type=Path)
    parser.add_argument('--not-comparable', action='store_true')
    args = parser.parse_args()
    old, new = read_json(args.old), read_json(args.new)
    atomic_json(args.output, advisory_diff(old['exposures'], new['exposures'], old['graph'], new['graph'], not args.not_comparable))


if __name__ == '__main__':
    main()
