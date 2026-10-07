"""A return-only guard does not obscure the subsequent local call result."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
prover = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / 'build/elisa-proof'
for name, accepted in (('guarded_call_result_bound', True),
        ('rejected_guarded_call_result_bound', False)):
    result = subprocess.run([str(prover), '--json',
        str(root / 'test/repro' / (name + '.elisa'))],
        capture_output=True, text=True, check=False)
    report = json.loads(result.stdout)
    assert report['summary']['semantic_errors'] == 0
    if accepted:
        assert result.returncode == 0 and report['status'] == 'proved', report['summary']
        assert report['replay']['gaps'] == 0
        assert report['replay']['replayed'] == report['replay']['certificates'] > 0
    else:
        assert result.returncode != 0 and report['summary']['unproven'] > 0
    print(name + (': complete replay' if accepted else ': refused'))
