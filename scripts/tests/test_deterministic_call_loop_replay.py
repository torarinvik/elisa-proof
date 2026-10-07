"""Adversarial checks for deterministic-call source sites inside and after loops and branches.

The replay walk reconstructs a call marker's actuals from the caller's source in statement
order. A loop may rewrite any binding on an earlier iteration, and a branch may or may not run,
so replay must accept only the opaque (name-only) form of such bindings: a marker that bakes in a
pre-loop, in-loop or single-branch value must not match the source call. The harness compiles the
current checker and replay modules with the freshness-checked Stage1 toolchain and calls the
source-site walk directly on markers built from the parsed call (exact span) and forged variants.
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

# Line numbers below are fixed by SOURCE_TEXT; keep them in step with it.
SOURCE_TEXT = (
    "def step(x: i64) -> i64:\n"  # 1
    "    return x + 1\n"  # 2
    "\n"  # 3
    "def looped(n: i64) -> i64:\n"  # 4
    "    t: mutable i64 = 0\n"  # 5
    "    k: mutable i64 = 0\n"  # 6
    "    while t < n:\n"  # 7
    "        k <- 7\n"  # 8
    "        d: i64 = step(t)\n"  # 9
    "        e: i64 = step(k)\n"  # 10
    "        t <- t + d - e + 7\n"  # 11
    "    return step(k)\n"  # 12
    "\n"  # 13
    "def branched(x: i64) -> i64:\n"  # 14
    "    v: mutable i64 = 0\n"  # 15
    "    if x > 0:\n"  # 16
    "        v <- 5\n"  # 17
    "    return step(v)\n"  # 18
)

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
        def test_loop_site_matches(report: ProofReport&, owner: sview, call: Ast::Expr) -> (known: bool, matches: usize):
            matches: mutable usize = 0
            known: bool = proof_replay_deterministic_call_source_declarations(report.source_declarations, owner, 0, call, Ast::expr_pos(call).line, &matches, 0)
            return (known, matches)

        # Exactly one source site: the replay acceptance condition.
        def test_loop_site_accepted(report: ProofReport&, owner: sview, call: Ast::Expr) -> bool:
            status: (known: bool, matches: usize) = test_loop_site_matches(report, owner, call)
            return status.known and status.matches == 1

using Ast
using ElisaProof

def test_loop_find_call_expr(expression: Ast::Expr, line: u32, found: mutable Ast::Expr&, hit: mutable bool&, depth: usize) -> void:
    if depth >= 64:
        return
    match expression:
        Ast::Expr.Call(Ast::Expr.Ident(callee, _), _, _, position):
            if callee == "step" and position.line == line:
                found <- expression
                hit <- true
        Ast::Expr.Block(statements, _, _, _):
            test_loop_find_call_statements(statements, line, found, hit, depth + 1)
        _:
            pass

def test_loop_find_call_statements(body: darray[Ast::Stmt]&, line: u32, found: mutable Ast::Expr&, hit: mutable bool&, depth: usize) -> void:
    if depth >= 64:
        return
    for statement in body |line, found, hit, depth|:
        match statement:
            Ast::Stmt.VarDecl(_, _, initializer, _):
                test_loop_find_call_expr(initializer, line, found, hit, depth + 1)
            Ast::Stmt.Assign(_, _, value, _):
                test_loop_find_call_expr(value, line, found, hit, depth + 1)
            Ast::Stmt.Expr(value, _):
                test_loop_find_call_expr(value, line, found, hit, depth + 1)
            Ast::Stmt.Return(value, _):
                test_loop_find_call_expr(value, line, found, hit, depth + 1)
            Ast::Stmt.If(_, yes, no, _):
                test_loop_find_call_statements(yes, line, found, hit, depth + 1)
                test_loop_find_call_statements(no, line, found, hit, depth + 1)
            Ast::Stmt.While(_, nested, _):
                test_loop_find_call_statements(nested, line, found, hit, depth + 1)
            _:
                pass

# The parsed `step(...)` call at `line` in `owner`, with its exact source span.
def test_loop_call(declarations: darray[Ast::Decl]&, owner: sview, line: u32) -> (known: bool, call: Ast::Expr):
    found: mutable Ast::Expr = Ast::Expr.Invalid
    hit: mutable bool = false
    for declaration in declarations |owner, line, found, hit|:
        match declaration:
            Ast::Decl.Func(name, _, _, body, _, _, _):
                if name == owner:
                    test_loop_find_call_statements(body, line, &found, &hit, 0)
            _:
                pass
    return (hit, found)

# The same call site with its sole actual replaced by an integer literal at the actual's span.
def test_loop_with_literal(call: Ast::Expr, value: i64) -> Ast::Expr:
    match call:
        Ast::Expr.Call(callee, arguments, names, position):
            return Ast::Expr.Invalid if arguments.count != 1
            literal: Ast::Expr = Ast::Expr.IntLit(value, Ast::expr_pos(arguments[0]))
            forged: darray[Ast::Expr] = [literal]
            return Ast::Expr.Call(callee, forged, names, position)
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

    # A call in a loop body binds the loop-rewritten actual opaquely.
    body_call: (known: bool, call: Ast::Expr) = test_loop_call(&report.source_declarations, "looped", 9)
    return 1 if not body_call.known
    return 2 if not test_loop_site_accepted(&report, "looped", body_call.call)
    # The pre-loop value `t = 0` holds only on the first iteration.
    return 3 if test_loop_site_accepted(&report, "looped", test_loop_with_literal(body_call.call, 0))
    return 4 if test_loop_site_accepted(&report, "looped", test_loop_shifted(body_call.call))
    return 5 if test_loop_site_accepted(&report, "looped", test_loop_with_literal(body_call.call, 1))

    # A binding the body assigns before the call is bound in statement order within the iteration.
    in_body_call: (known: bool, call: Ast::Expr) = test_loop_call(&report.source_declarations, "looped", 10)
    return 6 if not in_body_call.known
    return 7 if not test_loop_site_accepted(&report, "looped", in_body_call.call)
    return 9 if test_loop_site_accepted(&report, "looped", test_loop_with_literal(in_body_call.call, 0))

    # After the loop neither the pre-loop value nor the in-loop assignment is known to hold.
    after_call: (known: bool, call: Ast::Expr) = test_loop_call(&report.source_declarations, "looped", 12)
    return 10 if not after_call.known
    return 11 if not test_loop_site_accepted(&report, "looped", after_call.call)
    return 12 if test_loop_site_accepted(&report, "looped", test_loop_with_literal(after_call.call, 0))
    return 13 if test_loop_site_accepted(&report, "looped", test_loop_with_literal(after_call.call, 7))

    # After a one-armed branch the assigned name may hold either value.
    join_call: (known: bool, call: Ast::Expr) = test_loop_call(&report.source_declarations, "branched", 18)
    return 14 if not join_call.known
    return 15 if not test_loop_site_accepted(&report, "branched", join_call.call)
    return 16 if test_loop_site_accepted(&report, "branched", test_loop_with_literal(join_call.call, 0))
    return 17 if test_loop_site_accepted(&report, "branched", test_loop_with_literal(join_call.call, 5))
    # A wrong owner never matches.
    return 18 if test_loop_site_accepted(&report, "looped", join_call.call)
    return 0
'''


def main() -> None:
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    subprocess.run(["bash", str(FRESHNESS_CHECK), str(STAGE1)], check=True, cwd=COMPILER_ROOT)

    with tempfile.TemporaryDirectory(prefix="loop-call-replay-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source = directory / "loop_call_replay.elisa"
        executable = directory / "loop_call_replay"
        compiler_include = str(COMPILER_ROOT.resolve()) + "/"
        escaped = SOURCE_TEXT.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        harness = (
            HARNESS.replace("../../Elisa-compiler/", compiler_include)
            .replace('include "../src/', 'include "../../src/')
            .replace("SOURCE_TEXT_PLACEHOLDER", escaped)
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

    print("deterministic-call loop replay: loop-body and post-loop calls bind loop-written actuals opaquely; pre-loop, in-loop, single-branch, shifted-span and wrong-owner markers fail")


if __name__ == "__main__":
    main()
