"""The report adapter distinguishes valid non-success verdicts from malformed JSON."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "scripts/report_exit_status.py"


def classify(report_text):
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
        handle.write(report_text)
        handle.flush()
        return subprocess.run([sys.executable, str(ADAPTER), handle.name], capture_output=True, text=True)


proved = classify(json.dumps({
    "status": "proved", "verification_state": "proved",
    "summary": {"proven": 1, "obligations": 1}, "replay": {"gaps": 0},
}))
assert proved.returncode == 0 and proved.stdout.strip() == "0", proved

failed_unknown = classify(json.dumps({"status": "failed", "verification_state": "unknown"}))
assert failed_unknown.returncode == 0 and failed_unknown.stdout.strip() == "1", failed_unknown

# The census case is valid JSON and a non-success result, not a serialization failure.
replay_gap = classify(json.dumps({
    "status": "proved_with_replay_gaps",
    "verification_state": "unknown",
    "replay": {"gaps": 1},
}))
assert replay_gap.returncode == 0 and replay_gap.stdout.strip() == "1", replay_gap
assert "malformed" not in replay_gap.stderr

malformed = classify('{"status":')
assert malformed.returncode == 2 and "malformed --json output" in malformed.stderr, malformed

inconsistent = classify(json.dumps({
    "status": "proved_with_replay_gaps",
    "verification_state": "proved",
    "replay": {"gaps": 1},
}))
assert inconsistent.returncode == 2 and "invalid --json result lattice" in inconsistent.stderr, inconsistent

false_success = classify(json.dumps({"status": "failed", "verification_state": "proved"}))
assert false_success.returncode == 2 and "invalid --json result lattice" in false_success.stderr, false_success

partial_success = classify(json.dumps({
    "status": "proved", "verification_state": "proved",
    "summary": {"proven": 1, "obligations": 2}, "replay": {"gaps": 0},
}))
assert partial_success.returncode == 2 and "all obligations" in partial_success.stderr, partial_success

print("JSON report result lattice: proved, failed/unknown, replay-gap/unknown, malformed and inconsistent cases classified distinctly")
