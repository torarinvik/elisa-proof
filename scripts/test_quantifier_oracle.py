"""W-05 quantifier oracle, oracle half: positive, adversarial, malformed and budget cases. Needs
no elisa-proof binary; the Z3 cases are skipped (and say so) when z3 is not installed."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quantifier_oracle as oracle  # noqa: E402

BOUNDED = {"index": 0, "expr": "(forall j 0 n (<= (select xs j) 5))"}


def problem(goal, facts, arrays=("xs",)):
    return {"goal": goal, "facts": facts, "arrays": list(arrays), "terms": []}


def expect_malformed(name, value):
    try:
        oracle.query(value)
    except oracle.Malformed:
        return
    raise AssertionError(f"{name}: accepted a malformed problem")


# Malformed problems are refused before any solver runs.
expect_malformed("nested-forall", problem("(<= k n)", [{"index": 0, "expr": "(and (forall j 0 n (<= j n)) (<= 0 n))"}]))
expect_malformed("undeclared-array", problem("(<= (select ys k) 5)", [BOUNDED]))
expect_malformed("array-as-scalar", problem("(<= xs 5)", [BOUNDED]))
expect_malformed("reserved-name", problem("(<= elisa_q0 5)", [BOUNDED]))
expect_malformed("unknown-operator", problem("(=> (<= k n) (<= k n))", [BOUNDED]))
expect_malformed("unclosed", problem("(<= k n", [BOUNDED]))
expect_malformed("bad-forall", problem("(<= k n)", [{"index": 0, "expr": "(forall 0 n (<= j 1))"}]))
# Budgets: too many facts, too deep a goal.
expect_malformed("fact-budget", problem("(<= k n)", [{"index": i, "expr": "(<= 0 n)"} for i in range(oracle.MAX_FACTS + 1)]))
deep = "k"
for _ in range(oracle.MAX_DEPTH):
    deep = f"(+ {deep} 1)"
expect_malformed("depth-budget", problem(f"(<= {deep} n)", [BOUNDED]))

# Translating back keeps source terms and drops solver-made names.
names = {"k", "n", "xs__count"}
assert oracle.from_smt(["+", ["-", "1"], "k"], names) == "(+ -1 k)"
assert oracle.from_smt(["select", "xs", "k"], names) == "(select xs k)"
assert oracle.from_smt("xs__count", names) == "(count xs)"
assert oracle.from_smt(["+", "k!0", "k"], names) is None, "a skolem term must be dropped"
assert oracle.from_smt(["div", "k", "2"], names) is None, "an operator outside the grammar must be dropped"

# A record over the byte limit is not written.
assert oracle.record(3, [(0, "k")]) == '2 3 1 0 "k"'
assert oracle.record(3, [(0, "x" * oracle.MAX_RECORD_BYTES)]) is None

if shutil.which("z3") is None:
    print("quantifier oracle: z3 not installed; solver cases skipped, grammar cases passed")
    raise SystemExit(0)

# Positive: two unseen instances, xs[k - 1] and xs[k], of one bounded fact.
pair = oracle.solve(problem("(<= (+ (select xs (- k 1)) (select xs k)) 10)",
                            [BOUNDED, {"index": 1, "expr": "(and (<= 1 k) (< k n))"}]))
assert (0, "k") in pair and any(term in ("(+ -1 k)", "(- k 1)") for _, term in pair), pair
assert all(index == 0 for index, _ in pair), pair

# Positive: the fact index in the record is the problem's, not its position.
shifted = oracle.solve(problem("(<= (select xs k) 5)", [{"index": 7, "expr": "(forall j 0 n (<= (select xs j) 5))"},
                                                         {"index": 2, "expr": "(and (<= 0 k) (< k n))"}]))
assert shifted == [(7, "k")], shifted

# Adversarial: a false goal (k may equal n, one past the range) gets no instances.
assert oracle.solve(problem("(<= (select xs k) 5)", [BOUNDED, {"index": 1, "expr": "(and (<= 0 k) (<= k n))"}])) == []
# Adversarial: a goal that needs no quantifier yields no instance records.
assert oracle.solve(problem("(<= k n)", [BOUNDED, {"index": 1, "expr": "(< k n)"}])) == []

# End to end through --problems: one record per closable goal, nothing for the false one.
with tempfile.TemporaryDirectory() as directory:
    problems = Path(directory) / "problems.json"
    hints = Path(directory) / "hints.txt"
    problems.write_text(json.dumps({
        "4": problem("(<= (select xs k) 5)", [BOUNDED, {"index": 1, "expr": "(and (<= 0 k) (< k n))"}]),
        "5": problem("(<= (select xs n) 5)", [BOUNDED]),
        "6": {"goal": "(<= k"},
    }))
    run = subprocess.run([sys.executable, str(Path(oracle.__file__)), "--hints-out", str(hints), "--problems", str(problems)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    assert hints.read_text() == '2 4 1 0 "k"\n', hints.read_text()
    assert "goal 6: problem refused" in run.stderr, run.stderr

# Without a solver the oracle proposes nothing and still exits 0.
    missing = subprocess.run([sys.executable, str(Path(oracle.__file__)), "--problems", str(problems)],
                             capture_output=True, text=True, timeout=60, env={**__import__("os").environ, "ELISA_PROOF_Z3": "/nonexistent/z3"})
    assert missing.returncode == 0 and missing.stdout == "", (missing.returncode, missing.stdout)

print("quantifier oracle: instances found over source terms; false goals, skolems and malformed problems refused")
