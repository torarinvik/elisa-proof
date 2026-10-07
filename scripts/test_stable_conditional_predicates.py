import json
import os
import tempfile
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get('ELISA_PROOF_BIN', ROOT / 'build/elisa-proof'))
base = '''def bounded(byte: u8) -> u8:
    ensure result <= 2
    selected: u8 = 1 if CONDITION else 2
    selected
'''
cases = {'and': (base.replace('CONDITION','byte >= 48 and byte <= 57'), True),
         'or': (base.replace('CONDITION','byte == 48 or byte == 49'), True),
         'not': (base.replace('CONDITION','not (byte < 48)'), True),
         'nested': (base.replace('CONDITION','not (byte < 48 or byte > 57) and byte != 50'), True),
         'false-claim': (base.replace('CONDITION','byte >= 48 and byte <= 57').replace('result <= 2','result <= 1'), False),
         'reassigned': (base.replace('CONDITION','byte >= 48 and byte <= 57').replace('selected: u8','selected: mutable u8').replace('    selected\n','    selected <- 3\n    selected\n'), False)}
for name,(source,accepted) in cases.items():
    folder = tempfile.TemporaryDirectory()
    path=Path(folder.name) / (name+'.elisa');path.write_text(source)
    for route in ('--json','--function-json'):
        args=[str(BINARY),route]+(['bounded'] if route=='--function-json' else [])+[str(path)]
        result=subprocess.run(args,capture_output=True,text=True,timeout=60)
        report=json.loads(result.stdout)
        assert result.returncode == (0 if accepted else 1),(name,route,report['summary'])
        assert report['replay']['gaps']==0,(name,report['replay'])
        assert report['replay']['certificates']==report['replay']['replayed']
        assert not report['trust']['trusted_assumptions']
    print(name,'accepted' if accepted else 'refused')
