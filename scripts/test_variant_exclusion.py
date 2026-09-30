"""Variant exclusion: a match arm `x is E.V` also excludes every other variant of a uniquely named
enum, as a traced, replay-validated fact. Refuses a claim about the matched variant itself and
an enum name declared twice."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return result.returncode, json.loads(result.stdout)


code, data = run("variant_exclusion.elisa")
assert code == 0 and data["status"] == "proved" and data["findings"] == [], data["findings"]
assert data["summary"]["proven"] == 4 and data["replay"]["gaps"] == 0

for name, line in (("rejected_variant_exclusion.elisa", 10),
                   ("rejected_variant_exclusion_ambiguous.elisa", 14)):
    code, data = run(name)
    assert code == 1 and data["status"] == "failed" and data["replay"]["gaps"] == 0, data["findings"]
    assert [(f["name"], f["line"]) for f in data["findings"]] == [("arm", line)], data["findings"]

print("variant exclusion: sibling variants excluded, matched variant and ambiguous enum refuse")
