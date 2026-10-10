"""Focused failure status agrees with the diagnostic bound to that exact goal."""
import json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
binary=Path(os.environ.get("ELISA_PROOF_BIN",root/"build/elisa-proof")).resolve()
source=root/'examples/rejected_budget.elisa'
def query(*args):
    result=subprocess.run([str(binary),*map(str,args)],capture_output=True,text=True,timeout=60)
    return result.returncode,json.loads(result.stdout)
status,full=query('--json',source)
assert status==1 and full['status']=='failed'
expected={'too_wide_quantifier':'timeout','too_large_model':'timeout','unsupported_reasoning':'unknown','false_comparison':'disproved','too_many_congruence_terms':'timeout','too_many_congruence_rounds':'timeout','too_many_disjunctions':'timeout','too_deep_conditional':'timeout','too_deep_disjunctive_goal':'timeout'}
assert {f['name']:f['status'] for f in full['findings']}==expected
for finding in full['findings']:
    assert finding['goal_id'] is not None
    status,focused=query('--goal',finding['goal_id'],source)
    assert status==1
    assert focused['goal_id']==finding['goal_id']
    assert focused['goal']['name']==finding['name']
    assert focused['status']==expected[finding['name']],focused
    assert focused['failure']['status']==expected[finding['name']]
    assert focused['failure']['goal_id']==finding['goal_id']
    if finding['status']=='timeout':
        assert focused['failure']['counterexample_found'] is False
print('focused status: all nine exact-goal timeout, unknown and disproved classifications agree')
