"""Source-bound prefix instances replay; no whole-scanner admission is inferred."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

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
    if negative:
        assert report["source"]["status"] == "failed" and not report["source"]["complete"]
        assert result.returncode == 1 and report["status"] == "failed", report
        assert not report["tactic"]["valid"] or not report["tactic"]["solved"], report
    else:
        assert result.returncode == 0 and report["status"] == "proved", report
        assert report["admission_scope"] == "target"
        assert report["source"]["status"] == "proved" and report["source"]["complete"]
        assert report["source_goal_binding"]["previously_proven"]
        for key in ("valid", "solved", "trace_replayed", "kernel_trace_replayed", "kernel_replayed", "certificate_replayed"):
            assert report["tactic"][key], (key, report)
result = subprocess.run([BIN, "--tactics", str(ROOT / "examples/tactic_script_open_history_prefix_step.json"),
                         str(ROOT / "examples/open_history_length_prefix.elisa")],
                        capture_output=True, text=True, timeout=60)
report = json.loads(result.stdout)
assert result.returncode == 0 and report["status"] == "proved"
assert report["source_goal_binding"]["bound"] and report["source_goal_binding"]["fingerprint_match"]
assert report["tactic"]["valid"] and report["tactic"]["solved"]
assert report["admission_scope"] == "target" and report["source"]["complete"]
assert report["source_goal_binding"]["previously_proven"]
assert report["tactic"]["action_count"] == 9 and report["tactic"]["accepted_count"] == 9
assert report["tactic"]["trace_replayed"] and report["tactic"]["kernel_trace_replayed"]
assert report["tactic"]["kernel_replayed"] and report["tactic"]["certificate_replayed"]
# Binding must remain exact even when the source and tactic actions are otherwise valid.
with tempfile.TemporaryDirectory(prefix="elisa-prefix-fingerprint-") as temporary:
    script = json.loads((ROOT / "examples/tactic_script_whole_row_instance.json").read_text())
    script["target"]["goal_fingerprint"] ^= 1
    path = Path(temporary) / "wrong-fingerprint.json"
    path.write_text(json.dumps(script))
    refused = subprocess.run(
        [BIN, "--tactics", str(path), str(ROOT / "examples/open_quantified_prefix_elimination.elisa")],
        capture_output=True, text=True, timeout=60,
    )
    control = json.loads(refused.stdout)
    assert refused.returncode == 1 and control["status"] == "failed", control
    assert control["source_goal_binding"]["bound"], control
    assert not control["source_goal_binding"]["fingerprint_match"], control
    # Actions may solve the imported goal, but a mismatched binding must never
    # admit that result as the source-bound proof requested by the script.
    assert not control["tactic"]["valid"] and control["tactic"]["status"] == "failed", control
    assert "goal_fingerprint" in control["tactic"]["reason"], control
print("row-instance and explicit prefix-preservation proofs replay; false controls reject; complete length-prefix loop proves automatically")
