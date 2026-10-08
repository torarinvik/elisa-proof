"""Census diff comparison tests: fewer proved goals, a new gate, and a lost report fail; gains pass."""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from census_diff import retry_newly_unreadable, retry_timing_outliers

BASE = {"examples": 2, "proven": 5, "obligations": 6, "unreadable": [], "gates": {"no-rule": 1},
        "files": {"a.elisa": {"proven": 3, "obligations": 3, "gates": [], "seconds": 4.0},
                  "b.elisa": {"proven": 2, "obligations": 3, "gates": ["no-rule"]}}}


def diff(current):
    with tempfile.TemporaryDirectory() as scratch:
        base_path, cur_path = Path(scratch) / "base.json", Path(scratch) / "cur.json"
        base_path.write_text(json.dumps(BASE))
        cur_path.write_text(json.dumps(current))
        return subprocess.run([sys.executable, str(ROOT / "scripts/census_diff.py"), str(base_path), str(cur_path)],
                              capture_output=True, text=True)


def variant(edit):
    current = copy.deepcopy(BASE)
    edit(current)
    return current


assert diff(BASE).returncode == 0
gain = diff(variant(lambda c: c["files"]["b.elisa"].update(proven=3, gates=[])))
assert gain.returncode == 0 and "census gain: b.elisa" in gain.stdout, gain.stdout
drop = diff(variant(lambda c: c["files"]["a.elisa"].update(proven=2)))
assert drop.returncode == 1 and "a.elisa: proven 3 -> 2" in drop.stderr, drop.stderr
obligation_drop = diff(variant(lambda c: c["files"]["a.elisa"].update(obligations=2)))
assert obligation_drop.returncode == 1 and "a.elisa: obligations 3 -> 2" in obligation_drop.stderr, obligation_drop.stderr
obligation_growth = diff(variant(lambda c: c["files"]["a.elisa"].update(obligations=4)))
assert obligation_growth.returncode == 0 and "census coverage change: a.elisa: obligations 3 -> 4" in obligation_growth.stdout
gate = diff(variant(lambda c: c["files"]["b.elisa"].update(gates=["no-rule", "budget"])))
assert gate.returncode == 1 and "new refusal gates ['budget']" in gate.stderr, gate.stderr

slow = diff(variant(lambda c: c["files"]["a.elisa"].update(seconds=13.5)))
assert slow.returncode == 1 and "a.elisa: wall time 4.0s -> 13.5s" in slow.stderr, slow.stderr
assert diff(variant(lambda c: c["files"]["a.elisa"].update(seconds=12.5))).returncode == 0

noisy_timing = variant(lambda c: c["files"]["a.elisa"].update(seconds=13.5))
remeasurements = iter((8.0, 9.0))


def remeasure(path, timeout):
    assert path == ROOT / "examples/a.elisa"
    assert timeout == 600
    return "a.elisa", {"summary": {}}, next(remeasurements), None


retry_timing_outliers(BASE, noisy_timing, remeasure)
assert noisy_timing["files"]["a.elisa"]["seconds"] == 9.0
assert diff(noisy_timing).returncode == 0

persistent_slowdown = variant(lambda c: c["files"]["a.elisa"].update(seconds=13.5))
slow_remeasurements = iter((14.0, 15.0))
retry_timing_outliers(
    BASE, persistent_slowdown,
    lambda path, timeout: ("a.elisa", {"summary": {}}, next(slow_remeasurements), None),
)
assert persistent_slowdown["files"]["a.elisa"]["seconds"] == 14.0
assert diff(persistent_slowdown).returncode == 1

incomplete_recheck = variant(lambda c: c["files"]["a.elisa"].update(seconds=13.5))
retry_timing_outliers(BASE, incomplete_recheck,
                      lambda path, timeout: ("a.elisa", None, timeout, "timeout"))
assert incomplete_recheck["files"]["a.elisa"]["seconds"] == 13.5
assert diff(incomplete_recheck).returncode == 1


def lose(c):
    del c["files"]["a.elisa"]
    c["unreadable"] = ["a.elisa"]


lost = diff(variant(lose))
assert lost.returncode == 1 and "no longer produces a readable report" in lost.stderr, lost.stderr


def delete_input(c):
    del c["files"]["a.elisa"]


deleted = diff(variant(delete_input))
assert deleted.returncode == 1 and "source is absent" in deleted.stderr, deleted.stderr

transient = variant(lose)
transient["proven"] = 2
transient["obligations"] = 3
transient["unreadable_reasons"] = {"a.elisa": "timeout"}


def recovered(path, timeout):
    assert path == ROOT / "examples/a.elisa"
    assert timeout == 600
    return "a.elisa", {"summary": {"proven": 3, "obligations": 3}, "findings": []}, 1.5, None


retry_newly_unreadable(BASE, transient, recovered)
assert transient["unreadable"] == [] and "a.elisa" not in transient["unreadable_reasons"]
assert transient["proven"] == 5 and transient["obligations"] == 6
assert transient["files"]["a.elisa"]["seconds"] == 1.5

still_unreadable = variant(lose)
still_unreadable["unreadable_reasons"] = {"a.elisa": "timeout"}
retry_newly_unreadable(BASE, still_unreadable,
                       lambda path, timeout: ("a.elisa", None, timeout, "timeout"))
assert still_unreadable["unreadable"] == ["a.elisa"]
assert "a.elisa" not in still_unreadable["files"]

new_input_unreadable = variant(lambda c: c["unreadable"].append("new.elisa"))
retry_newly_unreadable(BASE, new_input_unreadable,
                       lambda path, timeout: ("new.elisa", None, timeout, "timeout"))
new_unreadable_result = diff(new_input_unreadable)
assert new_unreadable_result.returncode == 1
assert "new.elisa: newly unreadable input" in new_unreadable_result.stderr
print("census diff: proof/obligation drops, new gates, new unreadables, persistent 2x slowdowns fail; gains pass")

# Retries must honor the configured census worker budget, including empty work.
from unittest.mock import patch
import census_diff

for input_count, expected_workers in ((0, 1), (1, 1), (5, 2)):
    limited = copy.deepcopy(BASE)
    limited["unreadable"] = [f"retry-{i}.elisa" for i in range(input_count)]
    with patch.object(census_diff, "DEFAULT_WORKERS", 2), patch.object(
        census_diff, "ThreadPoolExecutor", wraps=census_diff.ThreadPoolExecutor
    ) as executor:
        retry_newly_unreadable(BASE, limited, lambda path, timeout: (path.name, None, timeout, "timeout"))
        executor.assert_called_once_with(max_workers=expected_workers)


# The live comparison guard includes post-census retries, not just the first run.
from unittest.mock import patch
import census_diff
from census_input_identity import input_identity

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    (root / "examples").mkdir()
    source = root / "examples/a.elisa"
    scratch = root / "scratch"
    scratch.mkdir()
    for mode in ("stable", "source", "product", "recorded"):
        source.write_text("initial\n")
        product = {"proof_binary_sha256": "original"}

        def initial_run(*args, **kwargs):
            current = copy.deepcopy(BASE)
            current["toolchain"] = dict(product,
                census_input_sha256=input_identity([source])["sha256"])
            if mode == "recorded":
                current["toolchain"]["census_input_sha256"] = "wrong-inputs"
            (scratch / "census.json").write_text(json.dumps(current))

        def retries(*args):
            if mode == "source":
                source.write_text("changed by retry\n")
            if mode == "product":
                product["proof_binary_sha256"] = "replacement"

        with patch.object(census_diff, "ROOT", root), \
             patch.object(census_diff, "DOGFOOD_SOURCES", ()), \
             patch.object(census_diff, "toolchain_identity", side_effect=lambda: dict(product)), \
             patch.object(census_diff.subprocess, "run", side_effect=initial_run), \
             patch.object(census_diff, "retry_newly_unreadable", side_effect=retries), \
             patch.object(census_diff, "retry_timing_outliers"):
            try:
                current = census_diff.live_census(BASE, scratch)
            except RuntimeError as error:
                assert mode != "stable", str(error)
            else:
                assert mode == "stable", f"accepted changed provenance: {mode}"
                assert current["proven"] == BASE["proven"]
print("census diff: live input/product provenance spans initial run and retries")
