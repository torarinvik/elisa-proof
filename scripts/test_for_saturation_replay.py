"""Decimal accumulator preservation authenticates source, bound and scope."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('ELISA_PROOF_BIN', str(ROOT / 'build/elisa-proof'))
BASE = (ROOT / 'examples/direct_digit_loop_replay_gap.elisa').read_text()
CASES = (
    ('valid', BASE, True),
    ('wrong-divisor', BASE.replace('/ 10', '/ 9'), False),
    ('wide-digit', BASE.replace('digit <= 9', 'digit <= 10'), False),
    ('no-bound', BASE.replace('    requires digit <= 9\n', ''), False),
    ('wrong-update', BASE.replace('value * 10 + digit', 'value * 11 + digit'), False),
    ('stale-exit', BASE.replace('ensure result <= 1000000', 'ensure result == 0'), False),
    ('earlier-write', BASE.replace('    for index', '    other: mutable u64 = 0\n    other <- other + 1\n    for index'), False),
)
for name, source, accepted in CASES:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'input.elisa'
        path.write_text(source)
        for route in ('--json', '--function-json'):
            args = [BINARY, route] + (['digit_loop'] if route == '--function-json' else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report['summary'])
            assert not report['trust']['trusted_assumptions']
            if accepted:
                assert report['summary']['obligations'] == 4
                assert report['summary']['proven'] == 4
                assert report['replay'] == {'certificates': 4, 'replayed': 4, 'gaps': 0}
            else:
                assert report['summary']['unproven'] > 0
    print('for saturation:', name, 'accepted' if accepted else 'refused')
