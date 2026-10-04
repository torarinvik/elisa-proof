#!/usr/bin/env python3
"""Pure function unfolding (BACKLOG D-04): positive, adversarial, malformed and budget cases."""
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BINARY = ROOT / "build/elisa-proof"


def report(source):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "probe.elisa"
        path.write_text(source)
        run = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=600)
    return json.loads(run.stdout)


def unproven_lines(result):
    return sorted({goal["line"] for goal in result["goals"] if not goal["proven"]})


def check(name, source, expected_unproven):
    result = report(source)
    lines = unproven_lines(result)
    assert lines == expected_unproven, f"{name}: unproven lines {lines}, expected {expected_unproven}"
    assert result["replay"]["gaps"] == 0, f"{name}: replay gaps"


def main():
    example = json.loads(subprocess.run([str(BINARY), "--json", str(ROOT / "examples/pure_unfolding.elisa")], capture_output=True, text=True, timeout=600).stdout)
    assert example["status"] == "proved" and example["replay"]["gaps"] == 0, "example must prove with no gaps"

    # Exact compound excluded middle must replay without exhausting case splits.
    predicate = "(c == 32 or c == 9 or c == 13)"
    for goal in (f"{predicate} or not {predicate}", f"not {predicate} or {predicate}"):
        check("compound-excluded-middle", f"def f(c: usize) -> usize:\n    ensures {goal}\n    return c\n", [])
    # Similar-looking alternatives are not complements. A failed helper cannot
    # lend a trusted summary to its caller.
    check("non-complement", f"def f(c: usize) -> usize:\n    ensures {predicate} or not (c == 32 or c == 9 or c == 14)\n    return c\n", [3])
    unverified = report("def bad(c: usize) -> bool:\n    ensures result\n    return c == 32\n\ndef caller(c: usize) -> usize:\n    requires bad(c)\n    ensures c == 32\n    return c\n")
    assert {goal["name"] for goal in unverified["goals"] if not goal["proven"]} == {"bad", "caller"}, "unverified helper summary became trusted"
    assert unverified["replay"]["gaps"] == 0

    # A loop guarded by a helper call cannot claim more than its range gives.
    rejected = json.loads(subprocess.run([str(BINARY), "--json", str(ROOT / "examples/rejected_helper_guarded_loop.elisa")], capture_output=True, text=True, timeout=600).stdout)
    assert rejected["status"] != "proved", "rejected_helper_guarded_loop must not prove"
    assert {finding["line"] for finding in rejected["findings"]} == {9}, "rejected_helper_guarded_loop: findings off the loop"
    helper = "def is_digit(c: i64) -> bool:\n    return c >= 48 and c <= 57\n\n"
    # Adversarial: the unfolded summary is exact, so a claim past it stays unproven.
    check("wrong-bound", helper + "def f(c: i64) -> i64:\n    requires is_digit(c)\n    ensures result <= 8\n    return c - 48\n", [7])
    # A written ensure disables synthesis; the weaker contract is all a caller sees.
    check("written-ensure", "def g(x: i64) -> i64:\n    requires x >= 0 and x <= 10\n    ensures result >= 0\n    return x + 1\n\ndef h(x: i64) -> i64:\n    requires x >= 0 and x <= 10\n    ensures result == x + 1\n    return g(x)\n", [9])
    # Recursion is refused: the helper has two statements and calls itself.
    check("recursive", "def r(n: i64) -> i64:\n    requires n >= 0 and n <= 10\n    if n == 0:\n        return 0\n    return r(n - 1)\n\ndef u(n: i64) -> i64:\n    requires n >= 0 and n <= 10\n    ensures result == 0\n    return r(n)\n", [10])
    # A body that calls another function is not unfolded.
    check("call-body", "def a(x: i64) -> i64:\n    requires x >= 0 and x <= 10\n    return x\n\ndef b(x: i64) -> i64:\n    requires x >= 0 and x <= 10\n    return a(x)\n\ndef c(x: i64) -> i64:\n    requires x >= 0 and x <= 10\n    ensures result == x\n    return b(x)\n", [12])
    # A helper with requires is not instantiated from a precondition, which proves nothing.
    check("guarded-helper", "def s(x: i64) -> i64:\n    requires x >= 0\n    return x - 1\n\ndef t(x: i64) -> i64:\n    requires s(x) >= 0 and x <= 10\n    ensures result >= 1\n    return x\n", [8])
    # Malformed: a struct return type never gets a synthesized `==`.
    struct = report("struct P:\n    x: i64\n\ndef mk(v: i64) -> P:\n    return P{x: v}\n")
    assert not any(finding["kind"].startswith("contract-") for finding in struct["findings"]), "struct-return: synthesized a contract"
    # Budget: a 24-node body unfolds, a 25-node body stays opaque.
    def chain(count):
        return " + ".join(["x"] * count)
    small = chain(12)
    large = chain(13)
    probe = "def k(x: i64) -> i64:\n    requires x >= 0 and x <= 10\n    return {body}\n\ndef m(x: i64) -> i64:\n    requires x >= 0 and x <= 10\n    ensures result == {body}\n    return k(x)\n"
    check("budget-in", probe.format(body=small), [])
    check("budget-out", probe.format(body=large), [8])
    print("pure unfolding: example, adversarial, malformed and budget cases pass")


if __name__ == "__main__":
    main()
