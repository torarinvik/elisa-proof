"""Source-bound prefix instances replay; no whole-scanner admission is inferred."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")

for script in ("whole_row_instance", "prefix_row_instance", "rejected_future_row_instance",
               "rejected_existential_row_instance", "rejected_empty_row_instance"):
    negative = script.startswith("rejected_")
    fixture = "rejected_quantified_prefix_elimination.elisa" if negative else "open_quantified_prefix_elimination.elisa"
    result = subprocess.run([BIN, "--tactics", str(ROOT / "examples" / f"tactic_script_{script}.json"),
                             str(ROOT / "examples" / fixture)], capture_output=True, text=True, timeout=60)
    report = json.loads(result.stdout)
    assert report["source_goal_binding"]["bound"]
    assert report["source_goal_binding"]["fingerprint_match"]
    assert report["source"]["admissible"] and report["source"]["fingerprint_match"]
    assert report["source"]["status"] == "failed" and not report["source"]["complete"]
    if negative:
        assert result.returncode == 1 and report["status"] == "failed", report
        assert not report["tactic"]["valid"] or not report["tactic"]["solved"], report
    else:
        assert result.returncode == 0 and report["status"] == "proved", report
        assert report["admission_scope"] == "target"
        assert not report["source_goal_binding"]["previously_proven"]
        for key in ("valid", "solved", "trace_replayed", "kernel_trace_replayed", "kernel_replayed", "certificate_replayed"):
            assert report["tactic"][key], (key, report)
result = subprocess.run([BIN, "--tactics", str(ROOT / "examples/tactic_script_open_history_prefix_step.json"),
                         str(ROOT / "examples/open_history_length_prefix.elisa")],
                        capture_output=True, text=True, timeout=60)
report = json.loads(result.stdout)
assert result.returncode == 0 and report["status"] == "proved"
assert report["source_goal_binding"]["bound"] and report["source_goal_binding"]["fingerprint_match"]
assert report["tactic"]["valid"] and report["tactic"]["solved"]
assert report["admission_scope"] == "target" and not report["source"]["complete"]
assert not report["source_goal_binding"]["previously_proven"]
assert report["tactic"]["action_count"] == 9 and report["tactic"]["accepted_count"] == 9
assert report["tactic"]["trace_replayed"] and report["tactic"]["kernel_trace_replayed"]
assert report["tactic"]["kernel_replayed"] and report["tactic"]["certificate_replayed"]
print("row-instance and explicit prefix-preservation proofs replay; false controls reject; automatic whole-loop admission remains open")
