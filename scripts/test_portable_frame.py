"""Portable frame predicates retain complete identities and refuse weaker rules."""
import copy
import json
import subprocess
from portable_replay_support import BINARY, ROOT, WORK, TRUST, replay, reseal, statement, with_theorem

source = WORK / "frame-positive.elisa"
source.write_text("struct Box:\n    value: mutable i64\n    other: mutable i64\ndef run(box: mutable Box&) -> void changes box.value preserves box.other:\n    box.value <- 1\n")
result = subprocess.run([str(BINARY), "--package", str(source)], capture_output=True, text=True, timeout=120)
assert result.returncode == 0, result.stderr
package = json.loads(result.stdout)
assert len(package["theorems"]) == 5
assert {t["rule"] for t in package["theorems"]} == {"frame-spec", "frame-allow", "frame-preserve", "resource-safety"}
for theorem in package["theorems"]:
    assert theorem["statement"] == statement(package, theorem["hypotheses"], theorem["conclusion"])
code, response = replay(package, "frame-positive")
assert code == 0 and response["summary"]["replayed"] == 5 and response["trust"] == TRUST, response

for negative, count, failed_goal in (("outside_rejected", 2, 1), ("preserve_rejected", 4, 3)):
    result = subprocess.run([str(BINARY), "--package", str(ROOT / "test/repro" / ("frame_accounting_" + negative + ".elisa"))], capture_output=True, text=True, timeout=120)
    rejected = json.loads(result.stdout)
    assert result.returncode == 0 and rejected["source"]["admissible"]
    assert len(rejected["theorems"]) == count and failed_goal not in {t["goal_id"] for t in rejected["theorems"]}
    code, subset = replay(rejected, "frame-valid-subset-" + negative)
    assert code == 0 and subset["summary"]["replayed"] == count

controls = 0
def reject(forged, label, reason=None):
    global controls
    code, response = replay(forged, label)
    assert code == 1 and response["status"] != "replayed", (label, response)
    assert reason is None or response["reason"] == reason, (label, response)
    controls += 1

allow = next(t for t in package["theorems"] if t["rule"] == "frame-allow")
preserve = next(t for t in package["theorems"] if t["rule"] == "frame-preserve")
for rule in ("frame-spec", "frame-allow", "frame-preserve", "goal"):
    if rule != preserve["rule"]:
        forged = with_theorem(package, preserve)
        forged["theorems"][0]["rule"] = rule
        reject(forged, "frame-relabel-" + rule)

# Without resealing, identity must bind parameter cardinality, partition split,
# actual place, ordered policy children, field labels and parameter ordinals.
for field in ("auxiliary", "right", "left"):
    forged = with_theorem(package, allow)
    node = forged["kernel"]["nodes"][allow["conclusion"]]
    node[field] += 1
    reject(forged, "frame-identity-" + field, "statement-mismatch" if field != "left" else None)
for target_kind, field, value in (("frame-field", "name", "different"), ("frame-place", "auxiliary", 1)):
    forged = with_theorem(package, allow)
    target = next(n for n in forged["kernel"]["nodes"] if n["kind"] == target_kind)
    target[field] = value
    reject(forged, "frame-identity-" + target_kind, "statement-mismatch")

forged = with_theorem(package, allow)
root = forged["kernel"]["nodes"][allow["conclusion"]]
children = forged["kernel"]["children"]
start = root["children_start"]
children[start], children[start + 1] = children[start + 1], children[start]
reject(forged, "frame-identity-ordered-policy", "statement-mismatch")

# A correctly resealed false predicate still fails kernel replay.
for theorem, label in ((allow, "outside"), (preserve, "overlap")):
    forged = with_theorem(package, theorem)
    nodes = forged["kernel"]["nodes"]
    root = nodes[theorem["conclusion"]]
    children = forged["kernel"]["children"]
    if label == "outside":
        root["left"] = children[root["children_start"] + root["right"]]
    else:
        children[root["children_start"]] = root["left"]
    reseal(forged, forged["theorems"][0])
    reject(forged, "frame-resealed-" + label)

for theorem in (allow, preserve):
    forged = with_theorem(package, theorem)
    forged["theorems"][0]["hypotheses"] = [theorem["conclusion"]]
    reseal(forged, forged["theorems"][0])
    reject(forged, "frame-injected-facts-" + theorem["rule"])
print("portable frame: all 5 certificates retained/replayed;", controls, "identity, relabelling, predicate and fact mutations refused")
