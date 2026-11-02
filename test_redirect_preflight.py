import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import redirect_preflight as rp


def csv(*rows):
    return ('source,target\n' + '\n'.join(','.join(r) for r in rows) + '\n').encode()


class Checks(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(rp.inspect(csv(('https://example.org/a', 'https://example.org/b')))['issues'], [])

    def test_chain_and_cycle(self):
        r = rp.inspect(csv(('https://example.org/a', 'https://example.org/b'),
                           ('https://example.org/b', 'https://example.org/c'),
                           ('https://example.org/c', 'https://example.org/b')))
        self.assertEqual([i['records'] for i in r['issues'] if i['kind'] == 'cycle'], [[3, 4]])
        self.assertEqual(sum(i['kind'] == 'chain_edge' for i in r['issues']), 3)

    def test_self_cycle(self):
        r = rp.inspect(csv(('https://example.org/a', 'https://example.org/a')))
        self.assertIn({'kind': 'cycle', 'records': [2]}, r['issues'])

    def test_duplicate_never_guessed(self):
        r = rp.inspect(csv(('https://example.org/a', 'https://example.org/b'),
                           ('https://example.org/a', 'https://example.org/c'),
                           ('https://example.org/z', 'https://example.org/a')))
        self.assertEqual([i['kind'] for i in r['issues']], ['duplicate_source', 'ambiguous_target'])

    def test_invalid(self):
        for v in ['relative', 'https://user:pass@example.org/a', 'https://example.org/a#x',
                  'https://example.org:bad/a', 'https://example.org/a b', 'https://example.org\\a']:
            self.assertFalse(rp.valid_url(v))
        self.assertEqual(rp.inspect(b'source,target\nx,y,z\n')['issues'][0]['kind'], 'invalid_record')
        for value in [b'bad,header\n', b'\xff', b'source,target\n"unterminated']:
            with self.assertRaises(ValueError): rp.inspect(value)

    def test_long_chain_iterative(self):
        r = rp.inspect(csv(*[(f'https://example.org/{i}', f'https://example.org/{i+1}') for i in range(5000)]))
        self.assertEqual(len(r['issues']), 4999)

    def test_exact_not_normalized(self):
        r = rp.inspect(csv(('https://example.org/a', 'https://example.org/B'),
                           ('https://example.org/b', 'https://example.org/c')))
        self.assertEqual(r['issues'], [])

    def test_limits_bom_and_multiline(self):
        self.assertEqual(rp.inspect(b'\xef\xbb\xbfsource,target\n')['issues'], [])
        with self.assertRaisesRegex(ValueError, 'input_limit'): rp.inspect(b'x' * (rp.MAX_BYTES + 1))
        with self.assertRaisesRegex(ValueError, 'row_limit'):
            rp.inspect(b'source,target\n' + b'x,y\n' * (rp.MAX_ROWS + 1))
        self.assertEqual(rp.inspect(b'source,target\n"https://example.org/a\nb",https://example.org/c\n')['issues'][0]['records'], [2])

    def test_real_cli_exit_privacy_and_unchanged_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'input.csv'
            for content, code in [(csv(('https://example.org/a', 'https://example.org/b')), 0),
                                  (csv(('https://example.org/a?private=SYNTHETIC', 'https://example.org/a?private=SYNTHETIC')), 1),
                                  (b'wrong\n', 2)]:
                p.write_bytes(content)
                before = hashlib.sha256(content).hexdigest()
                result = subprocess.run([sys.executable, str(Path(rp.__file__)), str(p)], capture_output=True, text=True)
                self.assertEqual(result.returncode, code)
                self.assertNotIn('SYNTHETIC', result.stdout + result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                json.loads(result.stdout)
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), before)
            result = subprocess.run([sys.executable, str(Path(rp.__file__)), str(Path(tmp) / 'missing')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout), {'error': 'input_unreadable'})


if __name__ == '__main__': unittest.main()
