"""Indexed-write frame (BACKLOG W-03).

Positive: after `xs[k] <- v` the written cell, a read at a provably different index, `xs.count`
and the bound beside an overwritten read in one conjunction are all kept, and every certificate
replays. Adversarial: a fact about the written cell, a read at an index not proved distinct and a
binding read before the write stay unproven. Malformed: a write through a call index keeps no
element fact. Budget: a write after 300 facts stays fast and replays.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-iwf-"))
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


positive = report(ROOT / "examples/indexed_write_frame.elisa")
check(positive is not None, "positive fixture produced no report")
if positive:
    summary = positive["summary"]
    check(summary["proven"] == summary["obligations"], f"positive fixture not fully proven: {summary}")
    check(positive["replay"]["gaps"] == 0, f"positive fixture has replay gaps: {positive['replay']}")

negative = report(ROOT / "examples/rejected_indexed_write_frame.elisa")
check(negative is not None, "adversarial fixture produced no report")
if negative:
    check(unproven_lines(negative) == {7, 13, 20}, f"adversarial unproven lines: {sorted(unproven_lines(negative))}")
    check(negative["replay"]["gaps"] == 0, f"adversarial fixture has replay gaps: {negative['replay']}")

malformed = WORK / "malformed.elisa"
malformed.write_text("""def pick(k: usize) -> usize:
    ensure result == k
    return k

def through_call(xs: mutable darray[i64], j: usize, k: usize) -> i64:
    requires j < xs.count and k < xs.count and j < k and xs[j] == 3
    ensure result == 3
    xs[pick(k)] <- 5
    return xs[j]
""")
data = report(malformed)
check(data is not None and 9 in unproven_lines(data), "a write through a call index kept an element fact")

budget = WORK / "budget.elisa"
facts = "".join(f"    requires n != {k}\n" for k in range(300))
budget.write_text(f"""def far(xs: mutable darray[i64], j: usize, k: usize, n: usize) -> i64:
    requires j < xs.count and k < xs.count and j < k and xs[j] == 3
{facts}    ensure result == 3
    xs[k] <- 5
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
print("indexed-write frame: written cell, other index, count and split bound kept and replayed; stale, alias, call index and budget refused")
