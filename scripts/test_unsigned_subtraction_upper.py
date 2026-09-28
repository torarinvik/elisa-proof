"""Regression for guarded subtraction, including independent replay and refusals."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(name, expected):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == expected, (name, run.returncode, run.stderr)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data
    assert data["replay"]["gaps"] == 0, data
    assert data["replay"]["replayed"] == data["replay"]["certificates"], data
    return data


positive = report("guarded_unsigned_subtraction_upper.elisa", 0)
assert positive["verification_state"] == "proved"
for name in ("guarded_word", "guarded_byte"):
    assert any(g["name"] == name and g["rule"] == "goal" and
               g["proven"] and g["replay_status"] == "replayed"
               for g in positive["goals"]), name

negative = report("rejected_unsigned_subtraction_upper.elisa", 1)
for name in ("unguarded_word", "zero_is_not_strict_decrease", "signed_negative_subtrahend"):
    assert any(f["name"] == name for f in negative["findings"]), name
    assert not any(g["name"] == name and g["rule"] == "goal" and g["proven"]
                   for g in negative["goals"]), name


def run(*arguments):
    return subprocess.run([str(BINARY), *arguments], capture_output=True, text=True, timeout=120)


# Repair must agree with source checking: it finds nothing to do where every goal already
# proves, and no tactic candidate may close a false subtraction or overflow goal.
clean = run("--repair-all", str(ROOT / "examples/guarded_unsigned_subtraction_upper.elisa"))
assert clean.returncode == 0, clean.stderr
assert json.loads(clean.stdout)["status"] == "nothing_to_repair", clean.stdout
for name, expected in (("rejected_unsigned_subtraction_upper.elisa", 3),
                       ("rejected_u64_max_conflict.elisa", 8)):
    repaired = run("--repair-all", str(ROOT / "examples" / name))
    assert repaired.returncode == 1, (name, repaired.returncode, repaired.stderr)
    batch = json.loads(repaired.stdout)
    assert batch["summary"]["repaired"] == 0, (name, batch["summary"])
    assert batch["summary"]["unresolved"] == expected, (name, batch["summary"])
    assert all(goal["status"] == "unrepaired" for goal in batch["goals"]), (name, batch["goals"])

# A rendered proof block is reused only by re-checking it against the source. The proved
# guarded goal reads back as a match; the open unguarded goal, relabelled `proof ... qed`,
# diverges instead of being admitted.
with tempfile.TemporaryDirectory() as directory:
    guarded = ROOT / "examples/guarded_unsigned_subtraction_upper.elisa"
    unguarded = ROOT / "examples/rejected_unsigned_subtraction_upper.elisa"
    proved_id = next(index for index, goal in enumerate(positive["goals"])
                     if goal["name"] == "guarded_word" and goal["rule"] == "goal" and goal["proven"])
    open_id = next(index for index, goal in enumerate(negative["goals"])
                   if goal["name"] == "unguarded_word" and not goal["proven"])
    proved_block = run("--proof", str(proved_id), str(guarded))
    assert proved_block.returncode == 0 and "\nproof guarded_word_" in proved_block.stdout, proved_block.stdout
    open_block = run("--proof", str(open_id), str(unguarded))
    assert open_block.returncode == 0 and "\nopen unguarded_word_" in open_block.stdout, open_block.stdout
    proved_path = Path(directory) / "proved.txt"
    proved_path.write_text(proved_block.stdout, encoding="utf-8")
    faithful = run("--check-proof", str(proved_path), str(guarded))
    assert faithful.returncode == 0 and json.loads(faithful.stdout)["status"] == "matches", faithful.stdout
    lines = [line for line in open_block.stdout.splitlines() if not line.startswith("    unproved:")]
    lines = [line.replace("open ", "proof ", 1) if line.startswith("open ") else line for line in lines]
    forged_path = Path(directory) / "forged.txt"
    forged_path.write_text("\n".join(lines + ["qed"]) + "\n", encoding="utf-8")
    forged = run("--check-proof", str(forged_path), str(unguarded))
    assert forged.returncode == 1 and json.loads(forged.stdout)["status"] == "diverges", forged.stdout
    # The proved block does not transfer to the unguarded source either.
    foreign = run("--check-proof", str(proved_path), str(unguarded))
    assert foreign.returncode == 1 and json.loads(foreign.stdout)["status"] != "matches", foreign.stdout

print("guarded unsigned subtraction: positive replay, three rejection controls, repair and proof-block reuse passed")
