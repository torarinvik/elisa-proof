"""Named record array extents and nested module spelling stay source checked."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('ELISA_PROOF_BIN', str(ROOT/'build/elisa-proof'))
BASE = '''const module Limits:
    CAP: usize = 4
struct Item:
    live: bool
struct Store:
    items: Item[Limits::CAP]
def read(store: Store&, index: usize) -> bool:
    requires index < 4
    ensure result == store.items[index].live
    store.items[index].live
'''
def module(source):
    return 'module Example:\n'+''.join('    '+line+'\n' for line in source.splitlines())
CASES = (
    ('named', BASE, True),
    ('literal', BASE.replace('Item[Limits::CAP]', 'Item[4]'), True),
    ('nested', module(BASE), True),
    ('private', 'module Example:\n    private:\n'+''.join('        '+line+'\n' for line in BASE.splitlines()), True),
    ('mutable', BASE.replace('struct Store:', 'affine struct Store:').replace('items: Item', 'items: mutable Item'), True),
    ('wrong-bound', BASE.replace('index < 4', 'index <= 4'), False),
    ('wrong-result', BASE.replace('ensure result == store', 'ensure result != store'), False),
    ('ambiguous-extent', module(BASE)+'module Other:\n    const module Limits:\n        CAP: usize = 9\n', False),
)
for name, source, accepted in CASES:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'input.elisa'; path.write_text(source)
        for route in ('--json', '--function-json'):
            args = [BINARY, route]+(['read'] if route=='--function-json' else [])+[str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report['summary'])
            assert not report['trust']['trusted_assumptions']
            if accepted:
                assert report['summary']['obligations'] == report['summary']['proven'] == 4
                assert report['replay']['gaps'] == 0
            else:
                assert report['summary']['unproven'] > 0
    print('record fixed array:', name, 'accepted' if accepted else 'refused')
