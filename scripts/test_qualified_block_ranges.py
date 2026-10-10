"""Qualified constants reach scoped value loops without namespace shadowing."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('ELISA_PROOF_BIN', str(ROOT/'build/elisa-proof'))
BASE = (ROOT/'examples/nested_record_loop_bound_gap.elisa').read_text()
INITIALIZER = BASE.replace('        for index', '        found: bool =\n            for index').replace('            all <-', '                all <-')+'        found\n'
CASES = (
    ('returned', BASE, True),
    ('initializer', INITIALIZER, True),
    ('private', BASE.replace('module Example:\n', 'module Example:\n    private:\n').replace('    const module', '        const module').replace('        CAP:', '            CAP:').replace('    struct', '        struct').replace('        live:', '            live:').replace('        items:', '            items:').replace('    def scan', '        def scan').replace('        for index', '            for index').replace('            all <-', '                all <-'), True),
    ('too-wide', BASE.replace('0..<Limits::CAP', '0..<(Limits::CAP + 1)'), False),
    ('parameter-shadow', BASE.replace('store: Store&', 'store: Store&, Limits: usize'), False),
    ('body-shadow', BASE.replace('            all <-', '            Limits: usize = 999\n            all <-'), False),
    ('initializer-shadow', INITIALIZER.replace('                all <-', '                Limits: usize = 999\n                all <-'), False),
)
for name, source, accepted in CASES:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'input.elisa'; path.write_text(source)
        for route in ('--json', '--function-json'):
            args = [BINARY, route]+(['scan'] if route=='--function-json' else [])+[str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report['summary'])
            assert not report['trust']['trusted_assumptions']
            if accepted:
                assert report['summary']['obligations'] >= 3
                assert report['summary']['proven'] == report['summary']['obligations']
                assert report['replay']['gaps'] == 0
            else:
                assert report['summary']['unproven'] > 0
    print('qualified block range:', name, 'accepted' if accepted else 'refused')
