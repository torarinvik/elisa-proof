"""Exercise deterministic, independent producer and replay disjunction work counters."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
COUNTER_KEYS = (
    "producer_disjunction_facts_scanned",
    "producer_disjunction_refutation_checks",
    "replay_disjunction_facts_scanned",
    "replay_disjunction_refutation_checks",
)


def run(source: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".elisa", encoding="utf-8") as stream:
        stream.write(source)
        stream.flush()
        process = subprocess.run(
            [BINARY, "--json", stream.name], capture_output=True, text=True, timeout=120
        )
    report = json.loads(process.stdout)
    assert process.returncode == 0 and report["status"] == "proved", report["findings"]
    assert report["summary"]["semantic_errors"] == 0
    assert report["replay"]["gaps"] == 0
    assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0
    assert not report["trust"]["trusted_assumptions"]
    measurements = report["measurements"]
    for key in COUNTER_KEYS:
        assert isinstance(measurements[key], int) and measurements[key] >= 0, measurements
    return report


# Irrelevant premises precede the useful one. The producer traverses the late candidate while
# replay independently repeats the refutation work without consulting producer counters.
late_source = "\n".join(
    [
        "def late_relevant(a: bool, b: bool, c: bool) -> bool:",
        "    requires (a or c) and (b or c)",
        "    ensure a or b or c",
        "    return true",
        "",
    ]
)
late = run(late_source)
late_work = tuple(late["measurements"][key] for key in COUNTER_KEYS)
assert 0 < late_work[0] <= 16, late_work
assert 0 <= late_work[1] <= 16, late_work
assert 0 < late_work[2] <= 8, late_work
assert 0 < late_work[3] <= 32, late_work
assert tuple(run(late_source)["measurements"][key] for key in COUNTER_KEYS) == late_work

# High-fact workload: many irrelevant disjunctions precede a correlated premise. Only an upper
# bound is normative: a more efficient index should be allowed to reduce this measured work.
high_fact_source = "\n".join(
    [
        "def high_fact_relevance(a: bool, b: bool, c: bool) -> bool:",
        *("    requires false or true" for _ in range(16)),
        "    requires (a or c) and (b or c)",
        "    ensure a or b or c",
        "    return true",
        "",
    ]
)
high_fact = run(high_fact_source)
high_work = tuple(high_fact["measurements"][key] for key in COUNTER_KEYS)
assert 0 < high_work[0] < 100_000, high_work
assert 0 < high_work[1] < 40_000, high_work
assert 0 < high_work[2] <= 20, high_work
assert 0 < high_work[3] < 500, high_work
assert tuple(run(high_fact_source)["measurements"][key] for key in COUNTER_KEYS) == high_work

print("disjunction work accounting: deterministic producer and independent replay counters passed")
