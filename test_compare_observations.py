import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from compare_observations import compare


def csv_bytes(header, rows):
    out = io.StringIO(newline='')
    writer = csv.writer(out); writer.writerow(header); writer.writerows(rows)
    return out.getvalue().encode()


class ObservationTests(unittest.TestCase):
    source = 'https://example.org/PRIVATE-FIXTURE'
    target = 'https://example.net/new'

    def mapping(self, rows=None):
        return csv_bytes(['source', 'target'], rows if rows is not None else [(self.source, self.target)])

    def observations(self, rows):
        return csv_bytes(['source', 'status', 'location'], rows)

    def report(self, status='301', location=None):
        return compare(self.mapping(), self.observations([(self.source, status, self.target if location is None else location)]))

    def test_clean_permanent_statuses(self):
        for status in ['301', '308']:
            report = self.report(status)
            self.assertEqual(report['issues'], [])
            self.assertEqual(report['matched_records'], 1)

    def test_nonpermanent_status_and_wrong_location(self):
        self.assertEqual([i['kind'] for i in self.report('307')['issues']], ['unexpected_status'])
        self.assertEqual([i['kind'] for i in self.report(location='/new')['issues']], ['location_mismatch'])
        self.assertEqual(len(self.report('200', '')['issues']), 2)

    def test_missing_and_unexpected(self):
        r = compare(self.mapping(), self.observations([('https://other.example/', '301', self.target)]))
        self.assertEqual([i['kind'] for i in r['issues']], ['missing_observation', 'unexpected_source'])
        self.assertEqual(r['issues'][0]['map_record'], 2)

    def test_duplicates_never_guessed(self):
        row = (self.source, '301', self.target)
        r = compare(self.mapping(), self.observations([row, row]))
        self.assertEqual(r['matched_records'], 0)
        self.assertEqual(r['issues'][0]['observation_records'], [2, 3])
        with self.assertRaisesRegex(ValueError, 'map_not_unique_or_valid'):
            compare(self.mapping([(self.source,self.target)]*2), self.observations([row]))

    def test_exact_case_and_trailing_slash(self):
        self.assertEqual(self.report(location=self.target+'/')['matched_records'], 0)
        r = compare(self.mapping(), self.observations([(self.source.upper(), '301', self.target)]))
        self.assertEqual(r['matched_records'], 0)

    def test_reject_malformed_without_value_echo(self):
        for data in [b'wrong\n', b'source,status,location\n\xff', b'source,status,location\na,b,c,d\n']:
            with self.assertRaises(ValueError): compare(self.mapping(), data)
        for status in ['0301', ' 301', '099', '600', '3a1']:
            with self.assertRaisesRegex(ValueError, 'invalid_observation'): self.report(status)
        with self.assertRaisesRegex(ValueError, 'invalid_observation'): self.report(location='bad\nheader')
        with self.assertRaisesRegex(ValueError, 'input_limit'): compare(self.mapping(), b'x'*2_000_001)

    def test_bom_and_empty_reports(self):
        r = compare(b'\xef\xbb\xbf'+self.mapping(), b'\xef\xbb\xbf'+self.observations([(self.source,'308',self.target)]))
        self.assertEqual(r['matched_records'],1)
        r=compare(self.mapping([]),self.observations([]))
        self.assertEqual(r['expected_records'],0); self.assertEqual(r['issues'],[])

    def test_cli_exits_privacy_and_unchanged_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            m=Path(d)/'map.csv'; o=Path(d)/'obs.csv'
            m.write_bytes(self.mapping())
            for status, location, code in [('301',self.target,0),('307',self.target,1),('301','/wrong',1),('bad',self.target,2)]:
                data=self.observations([(self.source,status,location)]); o.write_bytes(data)
                p=subprocess.run([sys.executable,'compare_observations.py',str(m),str(o)],capture_output=True)
                self.assertEqual(p.returncode,code); json.loads(p.stdout)
                self.assertNotIn(b'PRIVATE-FIXTURE',p.stdout+p.stderr)
                self.assertEqual(m.read_bytes(),self.mapping()); self.assertEqual(o.read_bytes(),data)
            o.write_bytes(self.observations([]))
            p=subprocess.run([sys.executable,'compare_observations.py',str(m),str(o)],capture_output=True)
            self.assertEqual(p.returncode,1)
            p=subprocess.run([sys.executable,'compare_observations.py',str(m),str(Path(d)/'absent')],capture_output=True)
            self.assertEqual(p.returncode,2); self.assertEqual(json.loads(p.stdout),{'error':'input_unreadable'})


if __name__ == '__main__': unittest.main()
