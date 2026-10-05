"""Compile the source-level producer/replay probe with the freshness-checked Stage1 toolchain.

This deliberately does not execute build/elisa-proof or build/elisa-proof-replay: they can be
from different source snapshots. The temporary Elisa executable includes the current checker
and replay modules directly, then forges only an in-memory deterministic-call trace.
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

using Ast
using ElisaProof

def main() -> i64 can[Memory.Allocate, Abort.Panic]:
    text: sview = "module Gate:\n    public:\n        def bounded(x: i64) -> i64:\n            requires x >= 0\n            ensure result >= 0\n            return x\n\ndef caller(x: i64) -> i64:\n    requires x >= 0\n    ensure result >= 0\n    return Gate::bounded(x)\n"
    source: mutable darray[u8] = []
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)
    proof_replay_certificates(&report)

    trace_index: mutable usize = report.fact_traces.count
    for index in 0..<report.fact_traces.count |index, report, trace_index|:
        if report.fact_traces[index].kind == "deterministic-call":
            trace_index <- index
            break
    return 1 if trace_index >= report.fact_traces.count
    return 2 if not proof_replay_fact_trace_entry(&report, trace_index)

    original: ProofFactTrace = report.fact_traces[trace_index]
    match original.expression:
        Ast::Expr.Call(marker_callee, marker_arguments, marker_names, position):
            return 3 if marker_arguments.count != 1
            match marker_arguments[0]:
                Ast::Expr.Call(_, arguments, argument_names, call_position):
                    forged_callee: Ast::Expr = Ast::Expr.Scope(Ast::Expr.Ident("Elsewhere", call_position), "bounded", call_position)
                    forged_call: Ast::Expr = Ast::Expr.Call(forged_callee, arguments, argument_names, call_position)
                    forged_arguments: darray[Ast::Expr] = [forged_call]
                    forged_expression: Ast::Expr = Ast::Expr.Call(marker_callee, forged_arguments, marker_names, position)
                    encoded: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_expression, &report, original.name)
                    return 4 if not encoded.known
                    report.fact_traces[trace_index] <- ProofFactTrace{expression: forged_expression, kernel_expression: encoded.root, kind: original.kind, line: original.line, name: original.name, dependency: original.dependency, premises_start: original.premises_start, premises_count: original.premises_count, kernel_premises_start: original.kernel_premises_start, kernel_premises_count: original.kernel_premises_count, summary_bindings_start: original.summary_bindings_start, summary_bindings_count: original.summary_bindings_count, summary_requires_start: original.summary_requires_start, summary_requires_count: original.summary_requires_count, summary_ensure_index: original.summary_ensure_index, owner_line: original.owner_line}
                    return 5 if proof_replay_fact_trace_entry(&report, trace_index)
                    report.fact_traces[trace_index] <- original
                    return 6 if not proof_replay_fact_trace_entry(&report, trace_index)
                _:
                    return 7
        _:
            return 8
    return 0
'''


def main() -> None:
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    subprocess.run(["bash", str(FRESHNESS_CHECK), str(STAGE1)], check=True, cwd=COMPILER_ROOT)

    with tempfile.TemporaryDirectory(prefix="qualified-call-replay-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source = directory / "qualified_call_replay.elisa"
        executable = directory / "qualified_call_replay"
        harness = HARNESS.replace("../../Elisa-compiler/", "../../../Elisa-compiler/").replace(
            'include "../src/', 'include "../../src/'
        )
        source.write_text(harness, encoding="utf-8")
        compiled = subprocess.run(
            [str(STAGE1_WRAPPER), "-emit", "exe", "-O2", "-o", str(executable), str(source)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=300,
        )
        if compiled.returncode:
            raise AssertionError(f"fresh Stage1 harness compile failed:\n{compiled.stdout}\n{compiled.stderr}")
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)

    print("qualified deterministic-call replay: producer witness accepted; wrong-module forgery rejected")


if __name__ == "__main__":
    main()
