"""Mutable captured-for entry facts are source checked, never reused as exit facts."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('ELISA_PROOF_BIN', str(ROOT/'build/elisa-proof'))
BASE = '''def entry(start: usize, stop: usize) -> usize:
    requires start <= stop and stop <= 100
    cursor: mutable usize = start
    count: mutable usize = 0
    for slot in 0..<9 |cursor, count|:
        invariant count <= 9
        invariant cursor <= stop
        count <- count
        cursor <- cursor
    0
'''
for name, source, expected in (
    ('entry', BASE, True),
    ('wrong-count', BASE.replace('count: mutable usize = 0','count: mutable usize = 10'), False),
    ('intervening-write', BASE.replace('    for slot','    count <- 10\n    for slot'), False),
    ('intervening-call', 'def overwrite(value: mutable usize&):\n    value <- 10\n\n'+BASE.replace('    for slot','    overwrite(&count)\n    for slot'), False),
):
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'input.elisa'
        path.write_text(source)
        for route in ('--json','--function-json'):
            args=[BINARY,route]+(['entry'] if route=='--function-json' else [])+[str(path)]
            done=subprocess.run(args,capture_output=True,text=True,timeout=60)
            report=json.loads(done.stdout)
            entries=[g for g in report['goals'] if g['name']=='entry' and g['rule']=='goal'
                     and not any(o['kind']=='loop-invariant' for o in g['fact_origins'])]
            # This controls entry replay only. Unrelated preservation bindings
            # in this minimal fixture remain unsupported, with a nonzero report.
            if expected:
                assert len(entries)==2 and all(g['proven'] and g['replay_status']=='replayed' for g in entries), (name,entries)
            else:
                assert any(not g['proven'] for g in entries), (name,entries)
                assert done.returncode != 0
            assert not report['trust']['trusted_assumptions']
    print('mutable for entry:',name,'accepted' if expected else 'refused')
