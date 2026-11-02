#!/usr/bin/env python3
"""Offline exact-string redirect CSV preflight. Python 3.10+, standard library."""
import argparse
import csv
import io
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

MAX_BYTES = 2_000_000
MAX_ROWS = 20_000


def valid_url(value):
    if not value or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    try:
        u = urlsplit(value)
        return (u.scheme in ('http', 'https') and bool(u.hostname)
                and u.username is None and u.password is None and not u.fragment
                and '\\' not in value and (u.port is None or 0 < u.port <= 65535))
    except ValueError:
        return False


def inspect(data):
    if len(data) > MAX_BYTES:
        raise ValueError('input_limit')
    try:
        reader = csv.reader(io.StringIO(data.decode('utf-8-sig'), newline=''), strict=True)
        if next(reader, None) != ['source', 'target']:
            raise ValueError('expected_source_target_header')
        rows = []
        issues = []
        sources = {}
        for record, row in enumerate(reader, 2):
            if record > MAX_ROWS + 1:
                raise ValueError('row_limit')
            if len(row) != 2 or not all(valid_url(v) for v in row):
                issues.append({'kind': 'invalid_record', 'records': [record]})
                continue
            source, target = row
            rows.append((record, source, target))
            sources.setdefault(source, []).append((record, target))
    except (UnicodeError, csv.Error):
        raise ValueError('invalid_utf8_or_csv') from None
    for entries in sources.values():
        if len(entries) > 1:
            issues.append({'kind': 'duplicate_source', 'records': [r for r, _ in entries]})
    # Ambiguous duplicate sources are excluded from graph analysis, never guessed.
    graph = {s: entries[0] for s, entries in sources.items() if len(entries) == 1}
    for record, source, target in rows:
        if source in graph and target in graph:
            issues.append({'kind': 'chain_edge', 'records': [record, graph[target][0]]})
        elif source in graph and target in sources:
            issues.append({'kind': 'ambiguous_target', 'records': [record] + [r for r, _ in sources[target]]})
    # Iterative functional-graph traversal; each node is completed once.
    completed = set()
    for start in graph:
        if start in completed:
            continue
        trail = []
        positions = {}
        current = start
        while current in graph and current not in completed and current not in positions:
            positions[current] = len(trail)
            trail.append(current)
            current = graph[current][1]
        if current in positions:
            cycle = trail[positions[current]:]
            issues.append({'kind': 'cycle', 'records': sorted(graph[s][0] for s in cycle)})
        completed.update(trail)
    issues.sort(key=lambda i: (i['records'][0], i['kind']))
    return {'format': 'redirect-preflight-v1', 'valid_records': len(rows), 'issues': issues,
            'comparison': 'exact_strings_no_network_no_normalization'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_file', help='UTF-8 CSV with source,target header')
    args = parser.parse_args(argv)
    try:
        with Path(args.csv_file).open('rb') as stream:
            data = stream.read(MAX_BYTES + 1)
        report = inspect(data)
    except OSError:
        print(json.dumps({'error': 'input_unreadable'}))
        return 2
    except ValueError as exc:
        print(json.dumps({'error': str(exc)}))
        return 2
    print(json.dumps(report, indent=2))
    return 1 if report['issues'] else 0


if __name__ == '__main__':
    sys.exit(main())
