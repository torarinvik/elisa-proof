"""Symbolic-range quantifiers (BACKLOG W-02).

Positive: cover, extend, empty, a later certificate in the shared arena and a fill loop's growing
invariant are proven and replayed by the kernel. Adversarial: an off-by-one extension, a wrong lower
bound, another body and a captured binder stay unproven. Malformed: a forall over a non-range is not
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
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True)
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
    check(positive["replay"]["gaps"] == 0 and positive["replay"]["replayed"] == positive["replay"]["certificates"],
          f"positive fixture has replay gaps: {positive['replay']}")

negative = report(ROOT / "examples/rejected_symbolic_quantifier.elisa")
check(negative is not None, "adversarial fixture produced no report")
if negative:
    names = {item.get("name") for item in negative["certificates"] if item.get("rule", "").startswith("quantifier")}
    for name in ("off_by_one", "wrong_lower", "other_body", "shadow"):
        check(name not in names, f"adversarial goal {name} was proven")
    check(negative["replay"]["gaps"] == 0, f"adversarial fixture has replay gaps: {negative['replay']}")

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
print("symbolic quantifiers: cover, extend, empty, fill loop replayed; adversarial, malformed and budget refused")
