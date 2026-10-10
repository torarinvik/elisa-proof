"""Authenticate readonly entry counts; stale or forged bindings fail closed."""
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
def test_source(text: sview, mode: i64) -> bool can[Memory.Allocate, Abort.Panic]:
    source: mutable darray[u8] = []
    for i in 0..<sview_len(text) |source|:
        source.push(sview_at(text, i))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)
    proof_replay_certificates(&report)
    report.replay_owner_line <- 1
    report.trace_owner_line <- report.certificates[0].line
    report.trace_consumer_certificate_index <- 1
    selected: mutable usize = report.traces.records.count
    for i in 0..<report.traces.records.count |report, selected|:
        if report.traces.records[i].name == "read" and report.traces.records[i].kind == "local-binding":
            selected <- i
            break
    return false if selected >= report.traces.records.count
    original: ProofFactTrace = report.traces.records[selected]
    report.traces.records.push(original) if mode == 1
    if mode == 2:
        match original.expression:
            Ast::Expr.Binary(left, operator, right, position):
                forged: Ast::Expr = Ast::Expr.Binary(left, operator, Ast::Expr.IntLit(0, position), position)
                encoded = proof_kernel_encode_annotated_checked(forged, &report, original.name)
                return false if not encoded.known
                report.traces.records[selected] <- ProofFactTrace{expression: forged, kernel_expression: encoded.root, kind: original.kind, line: original.line, name: original.name, dependency: original.dependency, premises_start: original.premises_start, premises_count: original.premises_count, kernel_premises_start: original.kernel_premises_start, kernel_premises_count: original.kernel_premises_count, summary_bindings_start: original.summary_bindings_start, summary_bindings_count: original.summary_bindings_count, summary_requires_start: original.summary_requires_start, summary_requires_count: original.summary_requires_count, summary_ensure_index: original.summary_ensure_index, owner_line: original.owner_line}
            _:
                return false
    return proof_replay_fact_trace_entry(&report, selected)

def main() -> i64 can[Memory.Allocate, Abort.Panic]:
    return 1 if not test_source("def read(v: mutable darray[u32]&) -> usize:\n    ensures result == old(v.count)\n    return v.count\n", 0)
    return 2 if test_source("def read(v: mutable darray[u32]&) -> usize:\n    ensures result == old(v.count)\n    return v.count\n", 1)
    return 3 if test_source("def read(v: mutable darray[u32]&) -> usize:\n    ensures result == old(v.count)\n    return v.count\n", 2)
    return 4 if test_source("def read(v: mutable darray[u32]&) -> usize:\n    ensures result == old(v.count)\n    v.push(3)\n    return v.count\n", 0)
    return 5 if test_source("def read(v: mutable darray[u32]&) -> usize:\n    ensures result == old(v.count)\n    v.pop()\n    return v.count\n", 0)
    return 6 if test_source("def read(v: mutable darray[u32]&) -> usize:\n    ensures result == old(v.count)\n    v[0] <- 3\n    return v.count\n", 0)
    return 7 if test_source("def read(v: mutable darray[u32]&) -> usize:\n    ensures result == old(v.count)\n    alias: mutable darray[u32]& = &v\n    alias.push(3)\n    return v.count\n", 0)
    return 0
'''

def main() -> None:
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    subprocess.run(["bash", str(FRESHNESS_CHECK), str(STAGE1)], check=True, cwd=COMPILER_ROOT)

    with tempfile.TemporaryDirectory(prefix="entry-count-source-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source = directory / "entry_count_source.elisa"
        executable = directory / "entry_count_source"
        compiler_include = str(COMPILER_ROOT.resolve()) + "/"
        harness = HARNESS.replace("../../Elisa-compiler/", compiler_include).replace(
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

    print("entry count source: readonly capture accepted; duplicate, forged, push/pop/write and borrowed alias refusals hold")


if __name__ == "__main__":
    main()
