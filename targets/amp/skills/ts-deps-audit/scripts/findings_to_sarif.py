#!/usr/bin/env python3
"""Convert an audit report JSON to SARIF without losing finding properties."""
import argparse
from pathlib import Path
from audit_core import atomic_json, read_json
from analysis import sarif


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    atomic_json(args.output, sarif(read_json(args.report)))


if __name__ == '__main__':
    main()
