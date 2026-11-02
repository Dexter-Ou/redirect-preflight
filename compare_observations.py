#!/usr/bin/env python3
"""Experimental offline exact-string map/HTTP-observation comparison. No network."""
import argparse
import csv
import io
import json
import sys
from pathlib import Path
from redirect_preflight import MAX_BYTES, MAX_ROWS, inspect, valid_url


def records(data, header):
    if len(data) > MAX_BYTES:
        raise ValueError('input_limit')
    try:
        reader = csv.reader(io.StringIO(data.decode('utf-8-sig'), newline=''), strict=True)
        if next(reader, None) != header:
            raise ValueError('unexpected_header')
        result = []
        for number, row in enumerate(reader, 2):
            if number > MAX_ROWS + 1:
                raise ValueError('row_limit')
            if len(row) != len(header):
                raise ValueError('invalid_record')
            result.append((number, row))
        return result
    except (UnicodeError, csv.Error):
        raise ValueError('invalid_utf8_or_csv') from None


def compare(map_data, observations_data):
    # Reuse map validation, but do not claim that observation matching clears
    # graph findings. Run redirect_preflight.py separately before import.
    map_report = inspect(map_data)
    if any(i['kind'] in ('invalid_record', 'duplicate_source') for i in map_report['issues']):
        raise ValueError('map_not_unique_or_valid')
    expected = {row[0]: (number, row[1])
                for number, row in records(map_data, ['source', 'target'])}
    observed = {}
    rows = records(observations_data, ['source', 'status', 'location'])
    for number, (source, status, location) in rows:
        if (not valid_url(source) or len(status) != 3
                or any(c not in '0123456789' for c in status)
                or not 100 <= int(status) <= 599
                or any(ord(c) < 32 or ord(c) == 127 for c in location)):
            raise ValueError('invalid_observation')
        observed.setdefault(source, []).append((number, status, location))
    issues = []
    matched = 0
    for source, (map_record, target) in expected.items():
        entries = observed.get(source, [])
        base = {'map_record': map_record, 'observation_records': [r[0] for r in entries]}
        if not entries:
            issues.append(dict(base, kind='missing_observation'))
        elif len(entries) > 1:
            issues.append(dict(base, kind='ambiguous_observation'))
        else:
            _, status, location = entries[0]
            if status not in ('301', '308'):
                issues.append(dict(base, kind='unexpected_status'))
            if location != target:
                issues.append(dict(base, kind='location_mismatch'))
            if status in ('301', '308') and location == target:
                matched += 1
    for source, entries in observed.items():
        if source not in expected:
            issues.append({'kind': 'unexpected_source', 'map_record': None,
                           'observation_records': [r[0] for r in entries]})
    return {'format': 'redirect-observation-experiment-v1',
            'expected_records': len(expected), 'observation_records': len(rows),
            'matched_records': matched, 'issues': issues,
            'comparison': 'exact_strings_supplied_observations_301_or_308_no_network'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map_csv')
    parser.add_argument('observations_csv')
    args = parser.parse_args(argv)
    try:
        data = []
        for name in (args.map_csv, args.observations_csv):
            with Path(name).open('rb') as stream:
                data.append(stream.read(MAX_BYTES + 1))
        report = compare(*data)
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
