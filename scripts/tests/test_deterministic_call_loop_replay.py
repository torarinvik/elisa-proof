"""Adversarial checks for deterministic-call source sites across loops, joins and writes.

The replay walk reconstructs a call marker's actuals from the caller's source in statement
order, expressed over the values names held at the latest reset point (function entry, loop
iteration entry, or a join that may have rewritten state). A marker must match only that
substituted call: one that bakes in a pre-loop, in-loop, single-branch or pre-mutation value, or
reads a reassigned name as its old value, must be refused. The harness compiles the current
checker and replay modules with the freshness-checked Stage1 toolchain and calls the source-site
walk directly on markers built from the parsed call (exact span) and forged variants.
"""

from pathlib import Path
import os
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
COMPILER_ROOT = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler"))
STAGE1 = COMPILER_ROOT / "bin" / "elisac-stage1"
STAGE1_WRAPPER = COMPILER_ROOT / "scripts" / "elisac_stage1.sh"
FRESHNESS_CHECK = COMPILER_ROOT / "scripts" / "assert_stage1_fresh.sh"

# The probe source is parsed and walked, not compiled, so it only has to parse.
SOURCE_LINES = [
    "def step(x: i64) -> i64:",
    "    return x + 1",
    "",
    "def looped(n: i64) -> i64:",
    "    t: mutable i64 = 0",
    "    k: mutable i64 = 0",
    "    while t < n:",
    "        k <- 7",
    "        d: i64 = step(t)",  # LOOP_BODY
    "        e: i64 = step(k)",  # LOOP_ASSIGNED
    "        t <- t + d - e + 7",
    "    return step(k)",  # LOOP_AFTER
    "",
    "def branched(x: i64) -> i64:",
    "    v: mutable i64 = 0",
    "    if x > 0:",
    "        v <- 5",
    "    return step(v)",  # BRANCH_AFTER
    "",
    "def bumped(a: i64) -> i64:",
    "    x: mutable i64 = a",
    "    while x < 10:",
    "        x <- x + 1",  # BUMP_ASSIGN
    "        r: i64 = step(x)",  # BUMP_CALL
    "    return 0",
    "",
    "def counted(n: i64) -> i64:",
    "    x: mutable i64 = 0",
    "    for i in 0..<n:",
    "        r: i64 = step(x)",  # FOR_CALL
    "        x <- x + 1",
    "    return 0",
    "",
    "def matched(k: i64) -> i64:",
    "    x: mutable i64 = 0",
    "    match k:",
    "        1:",
    "            x <- 5",
    "        _:",
    "            x <- 6",
    "    return step(x)",  # MATCH_AFTER
    "",
    "def pushed(a: i64) -> i64:",
    "    xs: mutable darray[i64] = []",
    "    xs.push(a)",
    "    return step(xs.count)",  # METHOD_AFTER
    "",
    "def shadowed(x: i64) -> i64:",
    "    z: i64 = x",
    "    x: i64 = 5",
    "    return step(z)",  # SHADOW_CALL
    "",
    "def guarded(n: i64) -> i64:",
    "    t: mutable i64 = 0",
    "    while step(t) < n:",  # GUARD_CALL
    "        t <- t + 1",
    "    return 0",
    "",
    "def nested(n: i64) -> i64:",
    "    t: mutable i64 = 0",
    "    while t < n:",
    "        u: mutable i64 = 0",
    "        while u < n:",
    "            u <- u + 1",
    "            if u > 3:",
    "                continue",
    "            r: i64 = step(u)",  # NESTED_CALL
    "        t <- t + 1",
    "    return 0",
    "",
    "def elsed(x: i64) -> i64:",
    "    v: mutable i64 = 0",
    "    if x > 0:",
    "        v <- 5",
    "    else:",
    "        if x < 0:",
    "            v <- 6",
    "    return step(v)",  # ELSE_AFTER
    "",
    "def compound(x: i64) -> i64:",
    "    v: mutable i64 = 0",
    "    if x > 0:",
    "        v += 5",
    "    return step(v)",  # COMPOUND_AFTER
    "",
]

TAGS = [
    "LOOP_BODY", "LOOP_ASSIGNED", "LOOP_AFTER", "BRANCH_AFTER", "BUMP_ASSIGN", "BUMP_CALL",
    "FOR_CALL", "MATCH_AFTER", "METHOD_AFTER", "SHADOW_CALL", "GUARD_CALL", "NESTED_CALL",
    "ELSE_AFTER", "COMPOUND_AFTER",
]


def tag_lines() -> dict:
    """One-based source line of each tagged probe line, read from the comments above."""
    text = Path(__file__).read_text(encoding="utf-8").splitlines()
    start = next(index for index, line in enumerate(text) if line.startswith("SOURCE_LINES = ["))
    lines = {}
    for offset, line in enumerate(text[start + 1 : start + 1 + len(SOURCE_LINES)]):
        for tag in TAGS:
            if line.rstrip().endswith("# " + tag):
                lines[tag] = offset + 1
    missing = [tag for tag in TAGS if tag not in lines]
    if missing:
        raise SystemExit(f"untagged probe lines: {missing}")
    return lines


HARNESS = r'''include "../../Elisa-compiler/elisacore_std/elisacore_runtime_prelude.elisa"
include "../../Elisa-compiler/elisacore_std/collections.elisa"
include "../../Elisa-compiler/elisacore_std/elisacore_runtime_strings.elisa"
include "../../Elisa-compiler/src/semantic/semantic.elisa"
include "../src/proof/kernel_core.elisa"
include "../src/proof/operator_impl_model.elisa"
include "../src/proof/model/enum_index.elisa"
include "../src/proof/model/findings.elisa"
include "../src/proof/model.elisa"
include "../src/proof/model/lemma_table.elisa"
include "../src/proof/model/report_invariants.elisa"
include "../src/proof/kernel.elisa"
include "../src/proof/kernel_intern.elisa"
include "../src/proof/expr.elisa"
include "../src/proof/linear.elisa"
include "../src/proof/resources.elisa"
include "../src/proof/check.elisa"
include "../src/proof/kernel_replay.elisa"
include "../src/proof/replay.elisa"
include "../src/proof/tactics.elisa"

extend ElisaProof:
    public:
        # Exactly one source site: the replay acceptance condition.
        def test_loop_site_accepted(report: ProofReport&, owner: sview, call: Ast::Expr) -> bool:
            matches: mutable usize = 0
            known: bool = proof_replay_deterministic_call_source_declarations(report.source_declarations, owner, 0, call, Ast::expr_pos(call).line, &matches, 0)
            return known and matches == 1

using Ast
using ElisaProof

def test_loop_find_expr(expression: Ast::Expr, line: u32, want_assign: bool, found: mutable Ast::Expr&, hit: mutable bool&, depth: usize) -> void:
    if depth >= 64:
        return
    match expression:
        Ast::Expr.Call(Ast::Expr.Ident(callee, _), arguments, _, position):
            if not want_assign and callee == "step" and position.line == line:
                found <- expression
                hit <- true
        Ast::Expr.Binary(left, _, right, _):
            test_loop_find_expr(left, line, want_assign, found, hit, depth + 1)
            test_loop_find_expr(right, line, want_assign, found, hit, depth + 1)
        Ast::Expr.Block(statements, _, _, _):
            test_loop_find_statements(statements, line, want_assign, found, hit, depth + 1)
        _:
            pass

def test_loop_find_statements(body: darray[Ast::Stmt]&, line: u32, want_assign: bool, found: mutable Ast::Expr&, hit: mutable bool&, depth: usize) -> void:
    if depth >= 64:
        return
    for statement in body |line, want_assign, found, hit, depth|:
        match statement:
            Ast::Stmt.VarDecl(_, _, initializer, _):
                test_loop_find_expr(initializer, line, want_assign, found, hit, depth + 1)
            Ast::Stmt.Assign(_, _, value, position):
                if want_assign and position.line == line:
                    found <- value
                    hit <- true
                test_loop_find_expr(value, line, want_assign, found, hit, depth + 1)
            Ast::Stmt.Expr(value, _):
                test_loop_find_expr(value, line, want_assign, found, hit, depth + 1)
            Ast::Stmt.Return(value, _):
                test_loop_find_expr(value, line, want_assign, found, hit, depth + 1)
            Ast::Stmt.If(condition, yes, no, _):
                test_loop_find_expr(condition, line, want_assign, found, hit, depth + 1)
                test_loop_find_statements(yes, line, want_assign, found, hit, depth + 1)
                test_loop_find_statements(no, line, want_assign, found, hit, depth + 1)
            Ast::Stmt.While(condition, nested, _):
                test_loop_find_expr(condition, line, want_assign, found, hit, depth + 1)
                test_loop_find_statements(nested, line, want_assign, found, hit, depth + 1)
            Ast::Stmt.For(_, _, _, nested, _):
                test_loop_find_statements(nested, line, want_assign, found, hit, depth + 1)
            _:
                pass

# The parsed `step(...)` call (or, with `want_assign`, the assigned value) at `line` in `owner`.
def test_loop_find(declarations: darray[Ast::Decl]&, owner: sview, line: u32, want_assign: bool) -> (known: bool, value: Ast::Expr):
    found: mutable Ast::Expr = Ast::Expr.Invalid
    hit: mutable bool = false
    for declaration in declarations |owner, line, want_assign, found, hit|:
        match declaration:
            Ast::Decl.Func(name, _, _, body, _, _, _):
                if name == owner:
                    test_loop_find_statements(body, line, want_assign, &found, &hit, 0)
            _:
                pass
    return (hit, found)

# The same call site, at its exact span, with its sole actual replaced.
def test_loop_with_argument(call: Ast::Expr, argument: Ast::Expr) -> Ast::Expr:
    match call:
        Ast::Expr.Call(callee, arguments, names, position):
            return Ast::Expr.Invalid if arguments.count != 1
            forged: darray[Ast::Expr] = [argument]
            return Ast::Expr.Call(callee, forged, names, position)
        _:
            return Ast::Expr.Invalid

def test_loop_with_literal(call: Ast::Expr, value: i64) -> Ast::Expr:
    match call:
        Ast::Expr.Call(_, arguments, _, _):
            return Ast::Expr.Invalid if arguments.count != 1
            return test_loop_with_argument(call, Ast::Expr.IntLit(value, Ast::expr_pos(arguments[0])))
        _:
            return Ast::Expr.Invalid

def test_loop_shifted(call: Ast::Expr) -> Ast::Expr:
    match call:
        Ast::Expr.Call(callee, arguments, names, position):
            shifted: mutable Ast::Pos = position
            shifted.column <- shifted.column + 1
            shifted.offset <- shifted.offset + 1
            shifted.end_column <- shifted.end_column + 1
            shifted.end_offset <- shifted.end_offset + 1
            return Ast::Expr.Call(callee, arguments, names, shifted)
        _:
            return Ast::Expr.Invalid

def main() -> i64 can[Memory.Allocate, Abort.Panic]:
    text: sview = "SOURCE_TEXT_PLACEHOLDER"
    source: mutable darray[u8] = []
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)

    # A loop-body call reads the loop-rewritten actual at iteration entry.
    body: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "looped", LOOP_BODY, false)
    return 1 if not body.known
    return 2 if not test_loop_site_accepted(&report, "looped", body.value)
    return 3 if test_loop_site_accepted(&report, "looped", test_loop_with_literal(body.value, 0))
    return 4 if test_loop_site_accepted(&report, "looped", test_loop_shifted(body.value))
    # An in-iteration assignment before the call binds that value, not the entry value.
    assigned: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "looped", LOOP_ASSIGNED, false)
    return 5 if not assigned.known
    return 6 if test_loop_site_accepted(&report, "looped", assigned.value)
    return 7 if test_loop_site_accepted(&report, "looped", test_loop_with_literal(assigned.value, 0))
    # After the loop neither the pre-loop value nor the in-loop assignment is known to hold.
    after: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "looped", LOOP_AFTER, false)
    return 8 if not after.known
    return 9 if not test_loop_site_accepted(&report, "looped", after.value)
    return 10 if test_loop_site_accepted(&report, "looped", test_loop_with_literal(after.value, 0))
    return 11 if test_loop_site_accepted(&report, "looped", test_loop_with_literal(after.value, 7))
    # A wrong owner never matches.
    return 12 if test_loop_site_accepted(&report, "branched", after.value)

    # After a one-armed branch the assigned name may hold either value.
    join: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "branched", BRANCH_AFTER, false)
    return 13 if not join.known
    return 14 if not test_loop_site_accepted(&report, "branched", join.value)
    return 15 if test_loop_site_accepted(&report, "branched", test_loop_with_literal(join.value, 0))
    return 16 if test_loop_site_accepted(&report, "branched", test_loop_with_literal(join.value, 5))

    # After `x <- x + 1` the raw `step(x)` would read the entry value; only `step(x + 1)` holds.
    bump_call: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "bumped", BUMP_CALL, false)
    bump_value: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "bumped", BUMP_ASSIGN, true)
    return 17 if not bump_call.known or not bump_value.known
    return 18 if test_loop_site_accepted(&report, "bumped", bump_call.value)
    return 19 if not test_loop_site_accepted(&report, "bumped", test_loop_with_argument(bump_call.value, bump_value.value))

    # A for body is entered after earlier iterations: the pre-loop value is not known.
    for_call: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "counted", FOR_CALL, false)
    return 20 if not for_call.known
    return 21 if not test_loop_site_accepted(&report, "counted", for_call.value)
    return 22 if test_loop_site_accepted(&report, "counted", test_loop_with_literal(for_call.value, 0))

    # Assignments in match arms are not lost at the join.
    match_call: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "matched", MATCH_AFTER, false)
    return 23 if not match_call.known
    return 24 if test_loop_site_accepted(&report, "matched", test_loop_with_literal(match_call.value, 0))
    return 25 if test_loop_site_accepted(&report, "matched", test_loop_with_literal(match_call.value, 5))
    return 26 if test_loop_site_accepted(&report, "matched", test_loop_with_literal(match_call.value, 6))

    # A method call may rewrite its receiver: the initializer value is stale afterwards.
    method_call: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "pushed", METHOD_AFTER, false)
    return 27 if not method_call.known
    return 28 if not test_loop_site_accepted(&report, "pushed", method_call.value)
    position: Ast::Pos = Ast::expr_pos(method_call.value)
    no_elements: darray[Ast::Expr] = []
    stale_count: Ast::Expr = Ast::Expr.Field(Ast::Expr.Array(no_elements, position), "count", position)
    return 29 if test_loop_site_accepted(&report, "pushed", test_loop_with_argument(method_call.value, stale_count))

    # A redeclared name makes the outer binding ambiguous: the function is refused.
    shadow_call: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "shadowed", SHADOW_CALL, false)
    return 30 if not shadow_call.known
    return 31 if test_loop_site_accepted(&report, "shadowed", shadow_call.value)
    return 32 if test_loop_site_accepted(&report, "shadowed", test_loop_with_argument(shadow_call.value, Ast::Expr.Ident("x", Ast::expr_pos(shadow_call.value))))

    # A call in the loop guard runs at every iteration entry.
    guard_call: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "guarded", GUARD_CALL, false)
    return 33 if not guard_call.known
    return 34 if not test_loop_site_accepted(&report, "guarded", guard_call.value)
    return 35 if test_loop_site_accepted(&report, "guarded", test_loop_with_literal(guard_call.value, 0))

    # Nested loops with a continue before the call: neither entry value holds at the call.
    nested_call: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "nested", NESTED_CALL, false)
    return 36 if not nested_call.known
    return 37 if test_loop_site_accepted(&report, "nested", nested_call.value)
    return 38 if test_loop_site_accepted(&report, "nested", test_loop_with_literal(nested_call.value, 0))
    return 39 if test_loop_site_accepted(&report, "nested", test_loop_with_literal(nested_call.value, 1))

    # if/else with a nested conditional assignment.
    else_call: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "elsed", ELSE_AFTER, false)
    return 40 if not else_call.known
    return 41 if not test_loop_site_accepted(&report, "elsed", else_call.value)
    return 42 if test_loop_site_accepted(&report, "elsed", test_loop_with_literal(else_call.value, 0))
    return 43 if test_loop_site_accepted(&report, "elsed", test_loop_with_literal(else_call.value, 5))
    return 44 if test_loop_site_accepted(&report, "elsed", test_loop_with_literal(else_call.value, 6))

    # A compound assignment in a branch.
    compound_call: (known: bool, value: Ast::Expr) = test_loop_find(&report.source_declarations, "compound", COMPOUND_AFTER, false)
    return 45 if not compound_call.known
    return 46 if test_loop_site_accepted(&report, "compound", test_loop_with_literal(compound_call.value, 0))
    return 0
'''


def main() -> None:
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    subprocess.run(["bash", str(FRESHNESS_CHECK), str(STAGE1)], check=True, cwd=COMPILER_ROOT)

    source_text = "\n".join(SOURCE_LINES) + "\n"
    escaped = source_text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    harness = HARNESS.replace("SOURCE_TEXT_PLACEHOLDER", escaped)
    for tag, line in tag_lines().items():
        harness = harness.replace(f", {tag},", f", {line},")

    with tempfile.TemporaryDirectory(prefix="loop-call-replay-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source = directory / "loop_call_replay.elisa"
        executable = directory / "loop_call_replay"
        compiler_include = str(COMPILER_ROOT.resolve()) + "/"
        harness = harness.replace("../../Elisa-compiler/", compiler_include).replace(
            'include "../src/', 'include "../../src/'
        )
        source.write_text(harness, encoding="utf-8")
        compiled = subprocess.run(
            [str(STAGE1_WRAPPER), "-emit", "exe", "-O2", "-o", str(executable), str(source)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=int(os.environ.get("ELISA_HARNESS_COMPILE_TIMEOUT", "300")),
        )
        if compiled.returncode:
            raise AssertionError(f"fresh Stage1 harness compile failed:\n{compiled.stdout}\n{compiled.stderr}")
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)

    print("deterministic-call loop replay: loop, guard, for, nested-loop and join calls bind rewritten actuals at their reset point; pre-loop, in-loop, single-arm, stale-receiver, reassigned-raw, shadowed, shifted-span and wrong-owner markers fail")


if __name__ == "__main__":
    main()
