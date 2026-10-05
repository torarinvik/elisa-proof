"""Symbolic-range quantifiers (BACKLOG W-02).

Positive: cover, extend, empty, weaken (also over a narrower range), a later certificate in the shared arena, a fill loop's growing
invariant, a bubble pass, an instance, a range lowered by its point, a range narrowed past a write, a bound
restated over a stepped symbol, a subscript read through an equal one, a full bubble sort, index congruence and a negated chain step are proven and replayed by the kernel. Adversarial: an off-by-one extension, a wrong lower
bound, another body and a captured binder, a weakening against the wrong bound and one over a wider range, a strict bubble invariant, congruence across another
subscript or container, a negated step read too strictly or backwards, an instance outside its range, a lowered range
missing its point or two short, a narrowing that keeps the written cell, a bound over another value, an
unequal subscript or another container's, and a strict, suffix-forgetting or one-pass-short sort stay unproven. Malformed: a forall over a non-range is not
taken by the rule. Budget: a covering fact past the 256-fact scan limit is not found, and the run
stays fast.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-symq-"))
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def report(path):
    try:
        result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        failures.append(f"{path.name} exceeded the 120-second proof-search deadline")
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def quantifier_goals(data, function):
    return [item for item in data["goals"] if item.get("function") == function and "forall" in json.dumps(item.get("goal", item))]


positive = report(ROOT / "examples/symbolic_quantifier.elisa")
check(positive is not None, "positive fixture produced no report")
if positive:
    summary = positive["summary"]
    check(summary["proven"] == summary["obligations"], f"positive fixture not fully proven: {summary}")
    steps = [fact for item in positive["certificates"] if item.get("name") == "binding_bound"
             for fact, origin in zip(item["facts"], item["fact_origins"]) if origin.get("kind") == "proof-step"
             and fact.get("operator") == "<" and fact["left"].get("name", "").startswith("__elisa_rebind")]
    check(steps, "binding_bound restated no bound over the stepped symbol")
    check(positive["replay"]["gaps"] == 0 and positive["replay"]["replayed"] == positive["replay"]["certificates"],
          f"positive fixture has replay gaps: {positive['replay']}")

triggered = report(ROOT / "examples/quantifier_trigger_instance.elisa")
check(triggered is not None, "goal-triggered scalar instance produced no report")
if triggered:
    check(triggered["summary"]["proven"] == triggered["summary"]["obligations"],
          f"goal-triggered scalar instance stayed open: {triggered['summary']}")
    check(triggered["replay"]["gaps"] == 0 and triggered["replay"]["certificates"] == triggered["replay"]["replayed"],
          f"goal-triggered scalar instance lacks checked replay evidence: {triggered['replay']}")

trigger_controls = report(ROOT / "examples/rejected_quantifier_trigger_instance.elisa")
check(trigger_controls is not None, "goal-triggered scalar adversarial fixture produced no report")
if trigger_controls:
    for name in ("trigger_free_search_is_refused", "captured_trigger_is_refused", "nested_call_capture_is_refused",
                 "nested_array_capture_is_refused", "out_of_range_trigger_is_refused"):
        check(any(item.get("name") == name and item.get("kind") == "ensure-unproven"
                  for item in trigger_controls["findings"]), f"trigger control {name} was not refused")
    check(trigger_controls["replay"]["gaps"] == 0, f"trigger controls have replay gaps: {trigger_controls['replay']}")

negative = report(ROOT / "examples/rejected_symbolic_quantifier.elisa")
check(negative is not None, "adversarial fixture produced no report")
if negative:
    names = {item.get("name") for item in negative["certificates"] if item.get("rule", "").startswith("quantifier")}
    for name in ("off_by_one", "wrong_lower", "other_body", "shadow", "weaken_wrong_way", "weaken_wider", "weaken_grown_missing_point", "element_not_strict"):
        check(name not in names, f"adversarial goal {name} was proven")
    for name in ("bubble_pass_strict", "congruence_other_index", "congruence_other_container", "negated_not_strict", "negated_wrong_direction", "guard_not_refuted", "guard_mentions_binder", "guard_not_negated",
                 "instance_outside", "lower_missing_point", "lower_two_short", "narrow_keeps_write", "binding_other_value",
                 "subscript_unequal", "subscript_other_container", "alias_outside", "alias_other_container", "alias_carried_outside"):
        check(any(item.get("name") == name and not item.get("proven") for item in negative["goals"]),
              f"adversarial function {name} has no unproven goal")
    check(not any(origin.get("kind") == "proof-step" and fact.get("operator") in ("<", "<=") and fact["left"].get("name", "").startswith("__elisa_rebind")
                  for item in negative["certificates"] + negative["goals"] if item.get("name") == "binding_other_value"
                  for fact, origin in zip(item["facts"], item["fact_origins"])), "a bound over k + 1 was restated over k + 2")
    check(negative["replay"]["gaps"] == 0, f"adversarial fixture has replay gaps: {negative['replay']}")

sort = report(ROOT / "examples/bubble_sort.elisa")
check(sort is not None and sort["summary"]["proven"] == sort["summary"]["obligations"] and sort["replay"]["gaps"] == 0,
      f"bubble sort not fully proven and replayed: {sort and sort['summary']}")
unsorted = report(ROOT / "examples/rejected_bubble_sort.elisa")
check(unsorted is not None, "rejected bubble sort produced no report")
if unsorted:
    for name in ("strict_order", "forgets_suffix", "one_pass_short"):
        check(any(item.get("name") == name and not item.get("proven") for item in unsorted["goals"]), f"rejected sort {name} fully proven")
    check(unsorted["replay"]["gaps"] == 0, f"rejected sort has replay gaps: {unsorted['replay']}")

split = report(ROOT / "examples/partition.elisa")
check(split is not None and split["summary"]["proven"] == split["summary"]["obligations"] and split["replay"]["gaps"] == 0,
      f"partition not fully proven and replayed: {split and split['summary']}")
unsplit = report(ROOT / "examples/rejected_partition.elisa")
check(unsplit is not None, "rejected partition produced no report")
if unsplit:
    for name in ("strict_upper", "forgets_upper", "swap_after_step"):
        check(any(item.get("name") == name and not item.get("proven") for item in unsplit["goals"]), f"rejected partition {name} fully proven")
    check(unsplit["replay"]["gaps"] == 0, f"rejected partition has replay gaps: {unsplit['replay']}")

malformed = WORK / "malformed.elisa"
malformed.write_text("""def not_range(values: darray[i64]&, n: usize) -> usize:
    requires forall i in values: i == 0
    ensure forall i in 0..<n: values[i] == 0
    return n
""")
data = report(malformed)
check(data is None or not any(item.get("rule", "").startswith("quantifier") for item in data["certificates"]),
      "a forall over a collection covered a range goal")

budget = WORK / "budget.elisa"
facts = "".join(f"    requires n != {k}\n" for k in range(300))
budget.write_text(f"""def far(values: darray[i64]&, n: usize, m: usize) -> usize:
    requires m <= n
{facts}    requires forall i in 0..<n: values[i] == 0
    ensure forall i in 0..<m: values[i] == 0
    return n
""")
start = time.monotonic()
data = report(budget)
elapsed = time.monotonic() - start
check(data is not None, "budget fixture produced no report")
if data:
    check(not any(item.get("rule", "").startswith("quantifier") for item in data["certificates"]),
          "a covering fact past the scan limit was used")
check(elapsed < 60, f"budget fixture took {elapsed:.1f}s")

if failures:
    for failure in failures:
        print("FAIL:", failure)
    raise SystemExit(1)
print("symbolic quantifiers: cover, extend, empty, fill loop, bubble sort and partition replayed; adversarial, malformed and budget refused")
