"""Case correlations survive OR introduction without adding proof-search fuel."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

if not __debug__:
    raise SystemExit("correlation checks must run without Python -O")
ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
REPLAY = Path(os.environ.get("ELISA_PROOF_REPLAY_BIN", ROOT / "build/elisa-proof-replay"))
SOURCE = ROOT / "examples/linear_disequality_refuted.elisa"


def report(path):
    run = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True,
                         text=True, timeout=60)
    data = json.loads(run.stdout)
    assert all(row["kind_code"] == 322 for row in data["semantic_diagnostics"]), data["semantic_diagnostics"]
    assert data["replay"]["gaps"] == 0, data["replay"]
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]
    assert all(not goal["proven"] or goal["replay_status"] == "replayed"
               for goal in data["goals"]), data["goals"]
    return run.returncode, data


status, positive = report(SOURCE)
assert status == 0 and positive["status"] == "proved", positive["findings"]
assert positive["summary"]["semantic_errors"] == 0, positive["summary"]
assert positive["summary"]["obligations"] == positive["summary"]["proven"] == 4
assert positive["replay"] == {"certificates": 4, "replayed": 4, "gaps": 0}

original = SOURCE.read_text()
with tempfile.TemporaryDirectory(prefix="elisa-correlated-disjunction-") as temporary:
    package_run = subprocess.run([str(BINARY), "--package", str(SOURCE)], capture_output=True,
                                 text=True, timeout=60)
    package = json.loads(package_run.stdout)
    assert package_run.returncode == 0 and len(package["theorems"]) == 4, package
    package_path = Path(temporary) / "correlated-package.json"
    package_path.write_text(json.dumps(package))
    replay_run = subprocess.run([str(REPLAY), str(package_path)], capture_output=True,
                                text=True, timeout=60)
    replay = json.loads(replay_run.stdout)
    assert replay_run.returncode == 0 and replay["status"] == "replayed", replay
    assert replay["summary"] == {"theorems": 4, "replayed": 4, "not_replayed": 0}, replay
    for name, changed in (
        ("one-alternative", original.replace("ensure ax != bx or ay != by", "ensure ax != bx")),
        ("missing-premise", original.replace("            requires not (bx - ax == 0 and by - ay == 0)\n", "")),
    ):
        assert changed != original
        source = Path(temporary) / (name + ".elisa")
        source.write_text(changed)
        status, negative = report(source)
        assert status == 1 and negative["status"] == "failed", (name, negative["summary"])
        failures = [goal for goal in negative["goals"]
                    if goal["name"] == "degenerate" and goal["rule"] == "goal"]
        assert len(failures) == 1 and not failures[0]["proven"], (name, failures)
        assert any(row["name"] == "degenerate" and row["kind"] == "ensure-unproven"
                   for row in negative["findings"]), (name, negative["findings"])

    # A true wrapping premise must not be read over unbounded integers when
    # denying the goal. x=127 makes the following i8 goal false.
    wrapped = Path(temporary) / "wrapping-goal.elisa"
    wrapped.write_text("""def wrapping_goal(x: i8) -> bool:
    requires x >= 126 and x <= 127
    requires x + 1 != 0
    ensure x + 1 != -128
    return true
""")
    status, negative = report(wrapped)
    assert status == 1 and negative["status"] == "failed", negative["summary"]
    assert any(goal["name"] == "wrapping_goal" and goal["rule"] == "goal" and not goal["proven"]
               for goal in negative["goals"]), negative["goals"]

print("correlated disjunction: all four obligations replay; false stronger and unguarded claims refused")
