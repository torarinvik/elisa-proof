"""Checked correspondence: `--correspondence <package.json> <file.elisa>`.

A package made from one source is checked against another. The positive cases pair each source
with its own package. Every mutation pairs a package with a source whose obligations differ from
what the package proves, while the package itself still replays: the kernel accepts every theorem,
so only the correspondence check stands between the package and a false `checked`.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-correspondence-"))
FORMAT = "elisa-proof-correspondence-v1"


def write(name, text):
    path = WORK / f"{name}.elisa"
    path.write_text(text)
    return path


def package(source):
    result = subprocess.run([str(BINARY), "--package", str(source)], capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, (source, result.stdout[-400:], result.stderr[-400:])
    path = WORK / f"{source.stem}.pkg.json"
    path.write_text(result.stdout)
    return path


def correspond(package_path, source, expected_exit):
    result = subprocess.run([str(BINARY), "--correspondence", str(package_path), str(source)], capture_output=True, text=True, timeout=300)
    assert result.returncode == expected_exit, (source, result.returncode, result.stdout[-1200:], result.stderr[-400:])
    report = json.loads(result.stdout)
    assert report["format"] == FORMAT, report
    assert report["summary"]["exit_code"] == expected_exit if "summary" in report else True, report
    return report


def statuses(report):
    return {entry["name"]: (entry["status"], entry["reason"]) for entry in report["functions"]}


def expect(package_path, source, expected, expected_exit):
    report = correspond(package_path, source, expected_exit)
    assert statuses(report) == expected, (source.name, statuses(report), report["functions"])
    return report


# Positive: every example of the subset matches its own package exactly.
POSITIVE = {
    "branch_negation": {"nonzero_or_one": ("checked", None)},
    "assignment_rhs_state": {"assignment_add_one": ("checked", None), "assignment_rhs_state": ("checked", None)},
    "for_invariant": {"count_nonnegative": ("checked", None)},
    "function_summary": {"identity_nonnegative": ("checked", None), "caller_uses_summary": ("checked", None)},
}
packages = {}
for example, expected in POSITIVE.items():
    source = ROOT / "examples" / f"{example}.elisa"
    packages[example] = package(source)
    report = expect(packages[example], source, expected, 0)
    for entry in report["functions"]:
        assert entry["obligations"] == entry["matched"] > 0 and entry["unmatched"] == [], entry
    assert report["package"]["status"] == "replayed" and report["source_admissible"] is True, report
    assert set(report["trust"]) == {"kernel_replay", "correspondence", "trusted", "not_established"}, report

# Mutations. Each package below replays in full; each source asks for something it does not prove.
BRANCH = packages["branch_negation"]
UNMATCHED = ("unmatched", "unproved-obligation")

# Swapped branch: the condition's facts now sit on the other path.
swapped = write("swapped", """def nonzero_or_one(x: i64) -> i64:
    ensure result != 0
    if x != 0:
        return 1
    else:
        return x
""")
report = expect(BRANCH, swapped, {"nonzero_or_one": UNMATCHED}, 1)
assert {item["kind"] for item in report["functions"][0]["unmatched"]} == {"return-ensure"}, report

# Negated branch fact: the same shape, but the false branch no longer carries `not (x == 0)`.
negated = write("negated", """def nonzero_or_one(x: i64) -> i64:
    ensure result != 0
    if not (x == 0):
        return 1
    else:
        return x
""")
expect(BRANCH, negated, {"nonzero_or_one": UNMATCHED}, 1)

# Weakened goal: the package proves `!= 0`; the source now demands `> 0`.
weakened = write("weakened", """def nonzero_or_one(x: i64) -> i64:
    ensure result > 0
    if x == 0:
        return 1
    else:
        return x
""")
expect(BRANCH, weakened, {"nonzero_or_one": UNMATCHED}, 1)

# Off-by-one bound: the package proves the ensure under `x > 0`; the source only tests `x >= 0`.
strict = write("strict_bound", """def positive_or_one(x: i64) -> i64:
    ensure result >= 1
    if x > 0:
        return x
    return 1
""")
loose = write("loose_bound", """def positive_or_one(x: i64) -> i64:
    ensure result >= 1
    if x >= 0:
        return x
    return 1
""")
expect(package(strict), strict, {"positive_or_one": ("checked", None)}, 0)
expect(WORK / "strict_bound.pkg.json", loose, {"positive_or_one": UNMATCHED}, 1)

# Added hypothesis: a theorem that assumes a second precondition the source dropped.
guarded = write("guarded", """def bounded(x: i64) -> i64:
    requires x >= 0
    requires x <= 10
    ensure result >= 0
    return x
""")
unguarded = write("unguarded", """def bounded(x: i64) -> i64:
    requires x >= 0
    ensure result >= 0
    return x
""")
expect(package(guarded), guarded, {"bounded": ("checked", None)}, 0)
expect(WORK / "guarded.pkg.json", unguarded, {"bounded": UNMATCHED}, 1)

# A fact from another function: `first`'s theorem assumes `x >= 0`, which holds in `first` but is
# not a fact in `second`, whose own precondition is a different proposition.
borrowed = write("borrowed", """def first(x: i64) -> i64:
    requires x >= 0
    ensure result >= 0
    return x

def second(x: i64) -> i64:
    requires x >= 1
    ensure result >= 0
    return x
""")
first_only = write("first_only", """def first(x: i64) -> i64:
    requires x >= 0
    ensure result >= 0
    return x
""")
expect(package(borrowed), borrowed, {"first": ("checked", None), "second": ("checked", None)}, 0)
expect(package(first_only), borrowed, {"first": ("checked", None), "second": UNMATCHED}, 1)

# Stale fact: a test on `y` before the loop says nothing about `y` after the loop assigns it.
loop_kept = write("loop_kept", """def kept(x: i64, n: i64) -> i64:
    requires n >= 0
    ensure result >= 0
    y: mutable i64 = 0
    for index in 0..<n:
        invariant y >= 0
        y <- y
    return y
""")
loop_stale = write("loop_stale", """def kept(x: i64, n: i64) -> i64:
    requires n >= 0
    ensure result >= 0
    y: mutable i64 = 0
    for index in 0..<n:
        y <- x
    return y
""")
expect(package(loop_kept), loop_kept, {"kept": ("checked", None)}, 0)
expect(WORK / "loop_kept.pkg.json", loop_stale, {"kept": UNMATCHED}, 1)

# Wrong callee ensure: the caller's package leans on `result == x`; the callee now promises less.
SUMMARY = packages["function_summary"]
weaker_callee = write("weaker_callee", """def identity_nonnegative(x: i64) -> i64:
    requires x >= 0
    ensure result >= x
    return x

def caller_uses_summary(x: i64) -> i64:
    requires x >= 0
    ensure result == x
    return identity_nonnegative(x)
""")
expect(SUMMARY, weaker_callee, {"identity_nonnegative": UNMATCHED, "caller_uses_summary": ("unsupported", "callee-unchecked")}, 1)
both_ensures = write("both_ensures", """def identity_nonnegative(x: i64) -> i64:
    requires x >= 0
    ensure result >= x
    ensure result == x
    return x

def caller_uses_summary(x: i64) -> i64:
    requires x >= 0
    ensure result == x
    return identity_nonnegative(x)
""")
weak_only = write("weak_only", """def identity_nonnegative(x: i64) -> i64:
    requires x >= 0
    ensure result >= x
    return x

def caller_uses_summary(x: i64) -> i64:
    requires x >= 0
    ensure result == x
    return identity_nonnegative(x)
""")
both_package = package(both_ensures)
expect(both_package, both_ensures, {"identity_nonnegative": ("checked", None), "caller_uses_summary": ("checked", None)}, 0)
expect(both_package, weak_only, {"identity_nonnegative": ("checked", None), "caller_uses_summary": UNMATCHED}, 1)

# Wrong arguments: the package proves facts about `f(x)` and `x >= 0`; the source calls `f(y)`.
two_arguments = write("two_arguments", """def identity_nonnegative(x: i64) -> i64:
    requires x >= 0
    ensure result == x
    return x

def caller_uses_summary(x: i64, y: i64) -> i64:
    requires x >= 0
    requires y >= 0
    ensure result == x
    return identity_nonnegative(x)
""")
other_argument = write("other_argument", """def identity_nonnegative(x: i64) -> i64:
    requires x >= 0
    ensure result == x
    return x

def caller_uses_summary(x: i64, y: i64) -> i64:
    requires x >= 0
    requires y >= 0
    ensure result == x
    return identity_nonnegative(y)
""")
expect(package(two_arguments), two_arguments, {"identity_nonnegative": ("checked", None), "caller_uses_summary": ("checked", None)}, 0)
report = expect(WORK / "two_arguments.pkg.json", other_argument, {"identity_nonnegative": ("checked", None), "caller_uses_summary": UNMATCHED}, 1)
assert {item["kind"] for item in report["functions"][1]["unmatched"]} == {"call-requires", "return-ensure"}, report

# A missing theorem: dropping one theorem from a replaying package leaves its obligation open.
trimmed = json.loads(BRANCH.read_text())
trimmed["theorems"] = [theorem for theorem in trimmed["theorems"] if theorem["line"] != 8]
assert len(trimmed["theorems"]) == 2
trimmed_path = WORK / "trimmed.pkg.json"
trimmed_path.write_text(json.dumps(trimmed))
report = expect(trimmed_path, ROOT / "examples/branch_negation.elisa", {"nonzero_or_one": UNMATCHED}, 1)
assert report["functions"][0]["unmatched"] == [{"line": 8, "kind": "return-ensure"}], report

# Unsupported: outside the subset nothing is claimed, and nothing checked means exit 1.
UNSUPPORTED = {
    "while_loop": ("""def spin(n: i64) -> i64:
    requires n >= 0
    ensure result >= 0
    total: mutable i64 = 0
    while total < n:
        total <- total + 1
    return total
""", "statement"),
    "division": ("""def half(x: i64) -> i64:
    requires x >= 0
    ensure result >= 0
    return x / 2
""", "expression"),
    "mutable_parameter": ("""def bump(x: mutable i64) -> i64:
    ensure result >= 0
    return 0
""", "parameter-type"),
    "self_call": ("""def again(x: i64) -> i64:
    requires x >= 0
    ensure result >= 0
    return again(x)
""", "callee-unchecked"),
    "shadowed_name": ("""def helper(x: i64) -> i64:
    ensure result >= 0
    helper: i64 = 0
    return helper
""", "name"),
    "return_in_loop": ("""def early(n: i64) -> i64:
    requires n >= 0
    ensure result >= 0
    for index in 0..<n:
        return 0
    return 0
""", "return-in-loop"),
    "binder_invariant": ("""def uses_binder(n: i64) -> i64:
    requires n >= 0
    ensure result >= 0
    total: mutable i64 = 0
    for index in 0..<n:
        invariant index >= 0
        total <- total
    return 0
""", "invariant"),
    "nested_call": ("""def one(x: i64) -> i64:
    ensure result == 1
    return 1

def two(x: i64) -> i64:
    ensure result == 2
    return one(x) + 1
""", "expression"),
}
for name, (text, reason) in UNSUPPORTED.items():
    source = write(name, text)
    report = correspond(BRANCH, source, 1)
    found = [entry for entry in report["functions"] if entry["status"] == "unsupported"]
    assert found and found[-1]["reason"] == reason, (name, report["functions"])
    assert found[-1]["obligations"] == 0 and found[-1]["unmatched"] == [], (name, report["functions"])

# A duplicate function name, one of them inside a module, resolves to neither.
duplicate = write("duplicate", """module Inner:
    def nonzero_or_one(x: i64) -> i64:
        return 1

def nonzero_or_one(x: i64) -> i64:
    ensure result != 0
    if x == 0:
        return 1
    else:
        return x
""")
report = correspond(BRANCH, duplicate, 1)
assert statuses(report) == {"nonzero_or_one": ("unsupported", "name")}, report

# A lemma is a ghost declaration, not an executable function: it is never walked, even when its
# obligations are proved. This source is admissible and its lemma's `ensure` is proved; the sweep
# over examples/ once reported the lemma `checked`.
lemma_source = ROOT / "examples/rejected_lemma_result.elisa"
report = correspond(package(lemma_source), lemma_source, 1)
assert report["source_admissible"] is True, report
assert statuses(report) == {"returning_fact": ("unsupported", "lemma"), "unbound_result_fact": ("unsupported", "return-type")}, report

# A type alias that renames a scalar type is not that scalar type.
aliased = write("aliased", """alias i64 = i32

def nonzero_or_one(x: i64) -> i64:
    ensure result != 0
    if x == 0:
        return 1
    else:
        return x
""")
report = subprocess.run([str(BINARY), "--correspondence", str(BRANCH), str(aliased)], capture_output=True, text=True, timeout=300)
assert report.returncode == 1, report
body = json.loads(report.stdout)
assert all(entry["status"] != "checked" for entry in body["functions"]), body

# An inadmissible source walks nothing.
inadmissible = write("inadmissible", """def nonzero_or_one(x: i64) -> i64:
    ensure result != 0
    if x == 0:
        return 1
    else:
        return missing_name
""")
report = correspond(BRANCH, inadmissible, 1)
assert report["source_admissible"] is False and all(entry["status"] == "" for entry in report["functions"]), report

# Budgets: nesting past the walker's bound is refused, not truncated.
deep_lines = ["def deep(x: i64) -> i64:", "    ensure result >= 0"]
for depth in range(70):
    deep_lines.append("    " * (depth + 1) + "if x >= 0:")
deep_lines.append("    " * 71 + "return 0")
deep_lines.append("    return 0")
deep = write("deep", "\n".join(deep_lines) + "\n")
report = correspond(BRANCH, deep, 1)
assert statuses(report) == {"deep": ("unsupported", "nesting")}, report
# A chain of locals composes into a value term deeper than the checker's term budget, although
# each line is shallow enough for the compiler.
chain = ["def chain(x: i64) -> i64:", "    ensure result >= 0", "    v0: i64 = x"]
chain += [f"    v{index + 1}: i64 = v{index} + 1" for index in range(140)]
chain.append("    return 0")
long_chain = write("long_chain", "\n".join(chain) + "\n")
report = correspond(BRANCH, long_chain, 1)
assert statuses(report) == {"chain": ("unsupported", "expression")}, report

# Malformed packages: no obligation is weighed against a package that does not replay.
source = ROOT / "examples/branch_negation.elisa"
bad_json = WORK / "bad.pkg.json"
bad_json.write_text("{\"format\": ")
report = correspond(bad_json, source, 1)
assert report["package"]["status"] == "malformed" and report["functions"] == [], report
forged = json.loads(BRANCH.read_text())
forged["theorems"][1]["statement"] = forged["theorems"][1]["statement"].replace("x", "y", 1)
forged_path = WORK / "forged.pkg.json"
forged_path.write_text(json.dumps(forged))
report = correspond(forged_path, source, 1)
assert report["package"]["status"] == "rejected" and report["functions"] == [], report
empty = json.loads(BRANCH.read_text())
empty["theorems"] = []
empty_path = WORK / "empty.pkg.json"
empty_path.write_text(json.dumps(empty))
report = correspond(empty_path, source, 1)
assert report["package"] == {"status": "rejected", "reason": "no-theorems", "theorems": 0, "replayed": 0}, report

# Usage and unreadable input exit 2.
result = subprocess.run([str(BINARY), "--correspondence", str(BRANCH)], capture_output=True, text=True, timeout=60)
assert result.returncode == 2 and "usage" in result.stdout, result
result = subprocess.run([str(BINARY), "--correspondence", str(WORK / "absent.json"), str(source)], capture_output=True, text=True, timeout=300)
assert result.returncode == 2 and json.loads(result.stdout)["package"]["status"] == "unreadable", result

print("correspondence tests passed")
