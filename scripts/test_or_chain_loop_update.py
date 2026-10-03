"""A conditional loop update guarded by a positive or-chain, `found <- index if found == stop and
(b == 32 or b == 9 or ...)`, proves as cheaply as its De Morgan spelling `not (b != 32 and ...)`.

The join of the update re-proves the branch condition in each arm. The goal search used to try
every left prefix of the chain, with full case splits over that same disjunctive fact, before the
plain assumption step, and tried each prefix twice more on the way back; the positive spelling
took 35-42 s against 1 s. The adversarial fixtures pin that the shortcuts decide nothing new: a
strict invariant, a wrong step and a wrong literal are still refused, a malformed chain is a
parse error, and a long chain stays bounded and claims nothing it does not replay."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
EXAMPLES = ROOT / "examples"


def run(name, timeout=120):
    started = time.monotonic()
    result = subprocess.run([str(BINARY), "--json", str(EXAMPLES / name)], capture_output=True, text=True, timeout=timeout)
    elapsed = time.monotonic() - started
    return result.returncode, json.loads(result.stdout), elapsed


def replayed(report):
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]


def failures(report):
    return sorted((finding["kind"], finding["line"]) for finding in report["findings"])


# Positive: both spellings prove every obligation and replay every certificate.
code, positive, positive_seconds = run("or_chain_loop_update.elisa")
assert code == 0 and positive["status"] == "proved", failures(positive)
assert positive["summary"]["proven"] == positive["summary"]["obligations"] == 12, positive["summary"]
replayed(positive)
code, de_morgan, de_morgan_seconds = run("or_chain_loop_update_de_morgan.elisa")
assert code == 0 and de_morgan["status"] == "proved", failures(de_morgan)
assert de_morgan["summary"]["proven"] == de_morgan["summary"]["obligations"] == 12, de_morgan["summary"]
replayed(de_morgan)
# Timing: the positive chain stays within a small factor of the De Morgan form. The floor keeps
# a fast machine's sub-second De Morgan run from turning scheduler noise into a failure.
assert positive_seconds < 6 * max(de_morgan_seconds, 1.0), (positive_seconds, de_morgan_seconds)
assert positive_seconds < 20, positive_seconds

# Adversarial: `found < stop` is false at entry, where `found` is `stop`.
code, strict, _ = run("rejected_or_chain_loop_strict_invariant.elisa")
assert code != 0 and strict["status"] == "failed", strict["status"]
replayed(strict)
assert ("invariant-unproven", 8) in failures(strict), failures(strict)
# Adversarial: `found <- index + 2` can leave `found` past `stop`.
code, step, _ = run("rejected_or_chain_loop_wrong_step.elisa")
assert code != 0 and step["status"] == "failed", step["status"]
replayed(step)
assert ("invariant-not-preserved", 8) in failures(step), failures(step)
# The literal shortcut in the congruence tier: a case `b == 32` proves `result == 32` ...
code, literal, _ = run("or_chain_literal_case.elisa")
assert code == 0 and literal["status"] == "proved", failures(literal)
replayed(literal)
# ... and never `result == 33`, which no premise names.
code, wrong_literal, _ = run("rejected_or_chain_literal_case.elisa")
assert code != 0 and wrong_literal["status"] == "failed", wrong_literal["status"]
replayed(wrong_literal)
assert [kind for kind, _ in failures(wrong_literal)] == ["ensure-unproven"], failures(wrong_literal)

# Malformed: a dangling `or` is a parse error, with no obligation and no certificate.
code, malformed, _ = run("malformed_or_chain_loop_update.elisa")
assert code != 0 and malformed["status"] == "failed", malformed["status"]
assert malformed["summary"]["obligations"] == 0 and malformed["replay"]["certificates"] == 0, malformed["summary"]
assert {kind for kind, _ in failures(malformed)} == {"parse-error"}, failures(malformed)

# Budget: a twelve-way chain exhausts the case-split budget at the join. It ends well inside the
# limit and refuses what it cannot decide; every goal it does claim replays.
code, long_chain, long_seconds = run("or_chain_loop_update_long.elisa")
assert long_seconds < 60, long_seconds
replayed(long_chain)
if long_chain["status"] != "proved":
    assert code != 0 and set(failures(long_chain)) <= {("invariant-not-preserved", 8), ("ensure-unproven", 8)}, failures(long_chain)

print(f"or-chain loop update: positive {positive_seconds:.2f}s, De Morgan {de_morgan_seconds:.2f}s; adversarial, malformed and budget fixtures hold")
