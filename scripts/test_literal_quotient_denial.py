"""Closed literal quotient guards replay without admitting invalid arithmetic."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('ELISA_PROOF_BIN', str(ROOT/'build/elisa-proof'))
TEMPLATE = '''def saturation(value: u64, byte: u64) -> u64:
    requires value <= CAP
    requires byte <= 255
    ensure result <= CAP
    digit: u64 = byte - 48 if byte >= 48 and byte <= 57 else 0
    CAP if value >= CAP / DIVISOR else value * 10 + digit
'''
for label, cap, divisor, accepted in (
    ('large', 1000000000000000000, 10, True),
    ('small', 1000000, 10, True),
    ('false-threshold', 1000000, 9, False),
    ('zero-divisor', 1000000, 0, False),
):
    source = TEMPLATE.replace('CAP', str(cap)).replace('DIVISOR', str(divisor))
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)/'input.elisa'
        path.write_text(source)
        for route in ('--json', '--function-json'):
            args = [BINARY, route]+(['saturation'] if route=='--function-json' else [])+[str(path)]
            run = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(run.stdout)
            assert run.returncode == (0 if accepted else 1), (label, route, report['summary'])
            assert report['replay']['gaps'] == 0, (label, report['replay'])
            assert report['replay']['certificates'] == report['replay']['replayed']
            assert not report['trust']['trusted_assumptions']
            if accepted:
                assert report['summary']['proven'] == report['summary']['obligations']
            else:
                assert report['status'] != 'proved'
    print('literal quotient:', label, 'accepted' if accepted else 'refused')
