"""A collection literal of up to eight elements has its length as a constant, read by comparison
in the producer and the replay kernel. Wrong lengths and a length outside that small comparison
table stay unproven, and every issued certificate independently replays."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


data = run(ROOT / "examples/literal_count.elisa")
assert data["summary"]["proven"] == 11 and data["summary"]["failed"] == 0 and data["findings"] == [], data["summary"]
assert data["replay"]["gaps"] == 0 and data["replay"]["replayed"] == 11

rejected = run(ROOT / "examples/rejected_literal_extent.elisa")
assert rejected["summary"]["semantic_errors"] == 0 and rejected["summary"]["failed"] == 8, rejected["summary"]
assert rejected["replay"]["gaps"] == 0 and rejected["replay"]["certificates"] == rejected["replay"]["replayed"], rejected["replay"]
claims = [goal for goal in rejected["goals"] if goal["rule"] == "goal"]
assert len(claims) == 7 and all(not goal["proven"] for goal in claims), claims
assert {finding["kind"] for finding in rejected["findings"]} == {"ensure-unproven", "index-upper-unproven"}, rejected["findings"]

print("literal count: short lengths prove and replay; wrong and unsupported lengths refuse cleanly")
