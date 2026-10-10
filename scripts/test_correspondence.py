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

if not __debug__:
    raise SystemExit("run without Python -O: correspondence assertions are required")

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


def refused_package(source):
    result = subprocess.run([str(BINARY), "--package", str(source)], capture_output=True, text=True, timeout=300)
    assert result.returncode != 0, (source, result.stdout[-400:], result.stderr[-400:])
    report = json.loads(result.stdout)
    assert report["source"]["admissible"] is False, report
    assert report["theorems"] == [], report
    return report


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
    assert report["summary"]["coverage"] == "complete", report
    assert set(report["trust"]) == {"kernel_replay", "correspondence", "trusted", "not_established"}, report

# A summary for a pure helper in the RHS of `or` is conditional on that branch. The current
# correspondence checker preserves the source obligation but cannot normalize the source return
# against the theorem's `result` term, so this remains an explicit unmatched gap.
short_circuit_summary = write("short_circuit_summary", """def available(x: i64) -> bool:
    ensure result == true
    return true

def caller() -> bool:
    ensure result == true
    return true or available(0)
""")
short_circuit_package = package(short_circuit_summary)
expect(short_circuit_package, short_circuit_summary,
       {"available": ("checked", None), "caller": ("unmatched", "unproved-obligation")}, 1)
false_unevaluated_helper = write("false_unevaluated_helper", """def available(x: i64) -> bool:
    ensure result == true
    return false

def caller() -> bool:
    ensure result == true
    return true or available(0)
""")
expect(short_circuit_package, false_unevaluated_helper,
       {"available": ("unmatched", "unproved-obligation"),
        "caller": ("unsupported", "callee-unchecked")}, 1)

variable_divisor = write("variable_divisor", """def quotient(value: i64, divisor: i64) -> i64:
    requires divisor > 0
    ensure result == value / divisor
    return value / divisor
""")
expect(package(variable_divisor), variable_divisor,
       {"quotient": ("unsupported", "contract")}, 1)
positive_divisor = write("positive_divisor", """def quotient(value: i64) -> i64:
    ensure result == value / 20
    return value / 20
""")
expect(package(positive_divisor), positive_divisor, {"quotient": ("checked", None)}, 0)
half_nonnegative = write("half_nonnegative", """def half(x: i64) -> i64:
    requires x >= 0
    ensure result >= 0
    return x / 2
""")
expect(package(half_nonnegative), half_nonnegative, {"half": ("checked", None)}, 0)
checked_helper_summary = write("checked_helper_summary", """def one(x: i64) -> i64:
    ensure result == 1
    return 1

def caller(x: i64) -> i64:
    ensure result == 1
    return one(x)
""")
checked_helper_package = package(checked_helper_summary)
checked_helper_report = expect(checked_helper_package, checked_helper_summary,
                               {"one": ("checked", None), "caller": ("checked", None)}, 0)
assert checked_helper_report["source_admissible"] is True, checked_helper_report
for name, divisor in (("zero_divisor", "0"), ("negative_divisor", "-1")):
    refused_division = write(name, f"""def quotient(value: i64) -> i64:
    ensure result == value / {divisor}
    return value / {divisor}
""")
    if divisor == "0":
        refused_report = refused_package(refused_division)
        assert refused_report["source"]["admissible"] is False, refused_report
    else:
        expect(package(refused_division), refused_division,
               {"quotient": ("unsupported", "contract")}, 1)

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

# Width: terms carry no types, so the width of `x + 1` is read from the operands' type facts. A
# theorem proved under i64 arithmetic assumes x's i64 bound, which a u8 source does not supply;
# at x == 255 the u8 sum wraps to 0.
wide_sum = write("wide_sum", """def f(x: i64) -> i64:
    requires x >= 0
    requires x <= 255
    ensure result >= 1
    return x + 1
""")
narrow_sum = write("narrow_sum", """def f(x: u8) -> u8:
    requires x >= 0
    requires x <= 255
    ensure result >= 1
    return x + 1
""")
expect(package(wide_sum), wide_sum, {"f": ("checked", None)}, 0)
expect(WORK / "wide_sum.pkg.json", narrow_sum, {"f": UNMATCHED}, 1)

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
}
for name, (text, reason) in UNSUPPORTED.items():
    source = write(name, text)
    report = correspond(BRANCH, source, 1)
    found = [entry for entry in report["functions"] if entry["status"] == "unsupported"]
    assert found and found[-1]["reason"] == reason, (name, report["functions"])
    assert found[-1]["obligations"] == 0 and found[-1]["unmatched"] == [], (name, report["functions"])
    assert report["summary"]["coverage"] == "not-established", report

# Literal positive division is supported and checked against its own package above. An unrelated
# package still replays but cannot discharge the source-derived return obligation.
mismatched_division = write("mismatched_division", half_nonnegative.read_text())
division_mismatch_report = expect(BRANCH, mismatched_division, {"half": UNMATCHED}, 1)
assert division_mismatch_report["package"]["status"] == "replayed", division_mismatch_report
assert division_mismatch_report["source_admissible"] is True, division_mismatch_report
assert division_mismatch_report["functions"][0]["obligations"] == 1, division_mismatch_report
assert division_mismatch_report["functions"][0]["unmatched"] == [
    {"line": 4, "kind": "return-ensure"}
], division_mismatch_report

# A checked helper's declared i64 result contributes only the scalar and signed-width facts for
# that exact resolved call. Its contract summary supplies the separate value equality.
nested_call_source = write("nested_call", """def one(x: i64) -> i64:
    ensure result == 1
    return 1

def two(x: i64) -> i64:
    ensure result == 2
    return one(x) + 1
""")
nested_call_package = package(nested_call_source)
nested_call_report = expect(nested_call_package, nested_call_source,
                            {"one": ("checked", None), "two": ("checked", None)}, 0)
assert nested_call_report["source_admissible"] is True, nested_call_report
nested_call_wrong_package = correspond(BRANCH, nested_call_source, 1)
assert nested_call_wrong_package["package"]["status"] == "replayed", nested_call_wrong_package
assert statuses(nested_call_wrong_package) == {
    "one": UNMATCHED, "two": ("unsupported", "callee-unchecked")
}, nested_call_wrong_package

# Cross-owner nested helper summaries still lack a replayable source proof. Until that evidence is
# available, package admission must fail closed instead of selecting a same-leaf declaration.
qualified_helper_owner = write("qualified_helper_owner", """module Policy:
    def one(x: i64) -> i64:
        ensure result == 1
        return 1

    def two(x: i64) -> i64:
        ensure result == 2
        return one(x) + 1

module Other:
    def one(x: i64) -> bool:
        ensure result == true
        return true
""")
refused_package(qualified_helper_owner)

# A shared leaf name in distinct owner paths is disambiguated by the source owner. The module
# function has no obligations; the root declaration matches the root-anchored package.
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
assert report["source_admissible"] is True, report
assert [(item["owner"], item["status"], item["reason"]) for item in report["functions"]] == [
    (["Inner"], "unmatched", "no-obligations"), ([], "checked", None)
], report

# Same-owner duplicate declarations and an unqualified root call to two nested owners are refused
# by source admission; neither can borrow whichever same-leaf declaration happened to be visited.
duplicate_same_owner = write("duplicate_same_owner", """def value(x: i64) -> i64:
    ensure result == 1
    return 1

def value(y: i64) -> i64:
    ensure result == 1
    return 1
""")
duplicate_report = correspond(BRANCH, duplicate_same_owner, 1)
assert duplicate_report["package"]["status"] == "replayed" and not duplicate_report["source_admissible"], duplicate_report
assert all(item["status"] != "checked" for item in duplicate_report["functions"]), duplicate_report

ambiguous_helper = write("ambiguous_helper", """module Policy:
    def helper(x: i64) -> i64:
        ensure result == 1
        return 1

module Other:
    def helper(x: i64) -> i64:
        ensure result == 1
        return 1

def caller() -> i64:
    ensure result == 1
    return helper(0)
""")
ambiguous_report = correspond(BRANCH, ambiguous_helper, 1)
assert ambiguous_report["package"]["status"] == "replayed" and not ambiguous_report["source_admissible"], ambiguous_report
assert all(item["status"] != "checked" for item in ambiguous_report["functions"]), ambiguous_report

# A lemma is a ghost declaration, not an executable function: it is never walked, even when its
# obligations are proved. This source is admissible and its lemma's `ensure` is proved; the sweep
# over examples/ once reported the lemma `checked`.
lemma_source = ROOT / "examples/rejected_lemma_result.elisa"
report = correspond(package(lemma_source), lemma_source, 1)
assert report["source_admissible"] is True, report
assert statuses(report) == {"returning_fact": ("unsupported", "lemma"), "unbound_result_fact": ("unsupported", "statement")}, report

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

# Budgets: nesting past the source-admission bound is refused, not partially walked.
deep_lines = ["def deep(x: i64) -> i64:", "    ensure result >= 0"]
for depth in range(70):
    deep_lines.append("    " * (depth + 1) + "if x >= 0:")
deep_lines.append("    " * 71 + "return 0")
deep_lines.append("    return 0")
deep = write("deep", "\n".join(deep_lines) + "\n")
report = correspond(BRANCH, deep, 1)
assert report["source_admissible"] is False and statuses(report) == {"deep": ("", None)}, report
# A chain of locals composes into a value term deeper than the checker's term budget, although
# each line is shallow enough for the compiler.
chain = ["def chain(x: i64) -> i64:", "    ensure result >= 0", "    v0: i64 = x"]
chain += [f"    v{index + 1}: i64 = v{index} + 1" for index in range(140)]
chain.append("    return 0")
long_chain = write("long_chain", "\n".join(chain) + "\n")
report = correspond(BRANCH, long_chain, 1)
assert statuses(report) == {"chain": ("unsupported", "budget")}, report

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
