"""Authenticate captured-loop entry inside a local initializer, never exit state."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('ELISA_PROOF_BIN', str(ROOT/'build/elisa-proof'))
BASE = '''def captured_initializer(limit: usize) -> usize:
    requires limit <= 32
    ensure result == 0
    found: usize =
        for slot in 0..<limit |found: usize = 32| -> found:
            invariant found <= 32
            found <- slot
    0
'''
for name, source, accepted in (
    ('entry', BASE, True),
    ('wrong-initial', BASE.replace('found: usize = 32', 'found: usize = 33'), False),
    ('wrong-update', BASE.replace('found <- slot', 'found <- 64'), False),
    ('stale-exit', BASE.replace('ensure result == 0', 'ensure result == 32').replace('    0\n', '    found\n'), False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'input.elisa'
        path.write_text(source)
        for route in ('--json', '--function-json'):
            args = [BINARY, route]+(['captured_initializer'] if route=='--function-json' else [])+[str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, report['summary'])
            if accepted:
                assert report['replay']['gaps'] == 0
                assert report['summary']['proven'] == report['summary']['obligations']
            else:
                assert report['summary']['unproven'] > 0
            assert not report['trust']['trusted_assumptions']
    print('captured initializer:', name, 'accepted' if accepted else 'refused')
