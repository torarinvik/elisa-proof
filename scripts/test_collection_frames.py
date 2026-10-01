"""Collection frames for swaps and pushes (BACKLOG W-04).

Positive: a swap through a temporary proves both swapped cells, and a push keeps element facts
and `j < xs.count` (a push only grows the count), even after a binding read, with every
certificate replayed. Adversarial: a read at an index not proved distinct from the swapped cells
and a stale `xs.count == 3` after a push stay unproven. Malformed: an element fact whose index
reads the count is not kept across a push. Budget: a push after 300 facts stays fast and replays.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-cf-"))
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


def unproven_lines(data):
    return {item["line"] for item in data["goals"] if not item["proven"]}


positive = report(ROOT / "examples/collection_frames.elisa")
check(positive is not None, "positive fixture produced no report")
if positive:
    summary = positive["summary"]
    check(summary["proven"] == summary["obligations"], f"positive fixture not fully proven: {summary}")
    check(positive["replay"]["gaps"] == 0, f"positive fixture has replay gaps: {positive['replay']}")

negative = report(ROOT / "examples/rejected_collection_frames.elisa")
check(negative is not None, "adversarial fixture produced no report")
if negative:
    check(unproven_lines(negative) == {7, 13, 19, 27}, f"adversarial unproven lines: {sorted(unproven_lines(negative))}")
    check(negative["replay"]["gaps"] == 0, f"adversarial fixture has replay gaps: {negative['replay']}")

malformed = WORK / "malformed.elisa"
malformed.write_text("""def last_cell(xs: mutable darray[i64]&, x: i64) -> i64 can[Memory.Allocate]:
    requires xs.count > 0 and xs[xs.count - 1] == 3
    ensure result == 3
    xs.push(x)
    return xs[0]
""")
data = report(malformed)
check(data is not None and 5 in unproven_lines(data), "an element fact indexed by the count survived a push")

budget = WORK / "budget.elisa"
facts = "".join(f"    requires n != {k}\n" for k in range(300))
budget.write_text(f"""def far(xs: mutable darray[i64]&, j: usize, n: usize, x: i64) -> i64 can[Memory.Allocate]:
    requires j < xs.count and xs[j] == 3
{facts}    ensure result == 3
    xs.push(x)
    return xs[j]
""")
start = time.monotonic()
data = report(budget)
elapsed = time.monotonic() - start
check(data is not None, "budget fixture produced no report")
if data:
    check(data["replay"]["gaps"] == 0, f"budget fixture has replay gaps: {data['replay']}")
check(elapsed < 60, f"budget fixture took {elapsed:.1f}s")

if failures:
    for failure in failures:
        print("FAIL:", failure)
    raise SystemExit(1)
print("collection frames: swapped cells and pushed-past element facts kept and replayed; aliased read, stale count, count-indexed fact and budget refused")
