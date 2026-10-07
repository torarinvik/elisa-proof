"""Owned call-initialized record fields retain their fixed storage extent."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('ELISA_PROOF_BIN', str(ROOT / 'build/elisa-proof'))
BASE = (ROOT / 'examples/local_record_fixed_index.elisa').read_text()
LOOP = 'struct Item:\n    value: i64\nstruct Store:\n    count: mutable usize\n    flags: mutable Item[3]\ndef make() -> Store:\n    Store{flags: zeroed, count: 0}\ndef checked() -> void:\n    store: mutable Store = make()\n    for index in 0..<3 |store|:\n        store.count <- index.usize()\n        store.flags[index] <- Item{value: 1}\n'
SHADOW = 'struct Item:\n    value: i64\nstruct Store:\n    flags: mutable Item[3]\ndef make() -> Store:\n    Store{flags: zeroed}\nstruct Small:\n    flags: mutable Item[2]\ndef small() -> Small:\n    Small{flags: zeroed}\ndef checked(index: usize) -> void:\n    store: mutable Store = make()\n    region inner_scope:\n        store: mutable Small = small()\n        return if index >= 3\n        store.flags[index] <- Item{value: 1}\n'
COUNT_BUDGET = (ROOT / 'examples/local_record_fixed_count_budget.elisa').read_text()
CASES = (
    ('fixed-count-budget', COUNT_BUDGET, True),
    ('fixed-count-budget-wide-guard', COUNT_BUDGET.replace('slot >= 3', 'slot >= 4'), False),
    ('fixed-count-budget-missing-guard', COUNT_BUDGET.replace('        return if slot >= 3\n', ''), False),
    ('captured-record-mutation', LOOP, True),
    ('captured-record-wide-loop', LOOP.replace('0..<3', '0..<4'), False),
    ('shadowed-smaller-record', SHADOW, False),
    ('shadowed-smaller-record-checked', SHADOW.replace('index >= 3', 'index >= 2'), True),
    ('record', BASE, True),
    ('qualified-extent', 'const module Limits:\n    CAP: usize = 3\n' + BASE.replace('Item[3]', 'Item[Limits::CAP]'), True),
    ('nested-array', BASE.replace('Item[3]', 'array[array[Item, 2], 3]').replace('store.flags[index] <- Item{value: 1}', 'store.flags[index] <- zeroed'), True),
    ('nested-wide-bound', BASE.replace('Item[3]', 'array[array[Item, 2], 3]').replace('store.flags[index] <- Item{value: 1}', 'store.flags[index] <- zeroed').replace('index >= 3', 'index >= 4'), False),
    ('borrowed-view-record', BASE.replace('struct Store:\n', 'struct Store:\n    hint: sview\n').replace('Store{flags: zeroed}', 'Store{flags: zeroed, hint: ""}'), False),
    ('wide-bound', BASE.replace('index >= 3', 'index >= 4'), False),
    ('missing-guard', BASE.replace('    return if index >= 3\n', ''), False),
    ('empty-storage', BASE.replace('Item[3]', 'Item[0]'), False),
    ('ambiguous-extent', 'const module Limits:\n    CAP: usize = 3\nconst module Limits:\n    CAP: usize = 4\n' + BASE.replace('Item[3]', 'Item[Limits::CAP]'), False),
)
for name, source, accepted in CASES:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'input.elisa'
        path.write_text(source)
        for route in ('--json', '--function-json'):
            args = [BINARY, route] + (['checked'] if route == '--function-json' else []) + [str(path)]
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
    print('local record fixed index:', name, 'accepted' if accepted else 'refused')
