"""Loop exit frames (BACKLOG W-04).

Positive: a nested loop keeps the outer `hi <= n` across the inner loop, and a fact over an
untouched parameter outlives a counting loop, with every certificate replayed. Adversarial: a
fact over a name the body assigns, writes an element of, or lends to a mutating call does not
survive. Malformed: a loop that writes through an unbounded alias keeps nothing. Budget: a loop
after 300 facts stays fast and replays.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-lef-"))
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def report(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        check(False, f"{path.name}: malformed report (exit {result.returncode})")
        return None
    expected = {"proved": 0, "failed": 1}.get(data.get("status"))
    check(expected is not None and result.returncode == expected,
          f"{path.name}: process/report mismatch (exit {result.returncode}, status {data.get('status')})")
    return data


def unproven_lines(data):
    return {item["line"] for item in data["goals"] if not item["proven"]}


positive = report(ROOT / "examples/loop_exit_frame.elisa")
check(positive is not None, "positive fixture produced no report")
if positive:
    summary = positive["summary"]
    check(summary["proven"] == summary["obligations"], f"positive fixture not fully proven: {summary}")
    check(positive["replay"]["gaps"] == 0, f"positive fixture has replay gaps: {positive['replay']}")

negative = report(ROOT / "examples/rejected_loop_exit_frame.elisa")
check(negative is not None, "adversarial fixture produced no report")
if negative:
    # The two line-6 obligations establish/preserve k <= n, not a bound on mutable a.
    # Both loop bounds replay, while all three stale post-loop claims remain unproven.
    check(unproven_lines(negative) == {10, 22, 36}, f"adversarial unproven lines: {sorted(unproven_lines(negative))}")
    bounds = [goal for goal in negative["goals"] if goal["name"] == "written_after_loop" and goal["line"] == 6]
    check(len(bounds) == 2 and all(goal["proven"] and goal["replay_status"] == "replayed" for goal in bounds),
          "loop bounds did not both prove and replay")
    check(negative["status"] == "failed" and negative["summary"]["semantic_errors"] == 0,
          "adversarial fixture must fail on proof obligations, not semantic errors")
    check(negative["replay"]["certificates"] == negative["replay"]["replayed"] == negative["summary"]["proven"],
          "adversarial certificate accounting mismatch")
    check(negative["replay"]["gaps"] == 0, f"adversarial fixture has replay gaps: {negative['replay']}")

malformed = WORK / "malformed.elisa"
malformed.write_text("""def through_slot(xs: mutable darray[i64]&, n: usize) -> i64:
    requires 0 < xs.count
    requires xs[0] == 3
    ensures result == 3
    k: mutable usize = 0
    while k < n:
        invariant k <= n
        xs[k] <- 4 if k < xs.count else 0
        k <- k + 1
    return xs[0]
""")
data = report(malformed)
check(data is None or len(unproven_lines(data)) > 0, "an element fact survived a loop writing a dynamic cell")

facts = "\n".join(f"    requires a < {1000 + index}" for index in range(300))
budget = WORK / "budget.elisa"
budget.write_text(f"""def many(a: i64, n: usize) -> i64:
{facts}
    ensures result < 1000
    k: mutable usize = 0
    while k < n:
        invariant k <= n
        k <- k + 1
    return a
""")
started = time.monotonic()
data = report(budget)
elapsed = time.monotonic() - started
check(elapsed < 60, f"a loop after 300 facts took {elapsed:.1f}s")
check(data is None or data["replay"]["gaps"] == 0, "budget fixture has replay gaps")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}")
    raise SystemExit(1)
print("loop exit frames: nested and untouched facts kept and replayed; assigned, element-written, lent, dynamic-cell and budget refused")
