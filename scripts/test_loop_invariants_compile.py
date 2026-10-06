"""Loops carrying `invariant` and `decreases` clauses compile, link and run under the pinned
compiler, and prove (BACKLOG E-03). Each invariant is then mutated, by negation and by tightening
a non-strict comparison, and every mutant must leave the proof incomplete: an invariant the
checker accepted without reading would survive a mutation."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
COMPILER = os.environ.get("ELISA_COMPILER_BIN", "")
FIXTURE = ROOT / "examples/loop_invariants_compile.elisa"
COMPILER_ROOT = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler"))
STAGE1 = COMPILER_ROOT / "bin/elisac-stage1"
STAGE1_WRAPPER = COMPILER_ROOT / "scripts/elisac_stage1.sh"
STAGE1_FRESHNESS = COMPILER_ROOT / "scripts/assert_stage1_fresh.sh"
PINNED_FRONTEND_ROOT = ROOT / "build/snapshot/Elisa-compiler"
PINNED_FRONTEND_REV = (ROOT / "ELISA_COMPILER_REV").read_text().strip()

REPLAY_HARNESS = r'''include "../../Elisa-compiler/elisacore_std/elisacore_runtime_prelude.elisa"
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
include "../src/proof/tactics.elisa"
include "../src/proof/check.elisa"
include "../src/proof/kernel_replay.elisa"
include "../src/proof/replay.elisa"

using Ast
using ElisaProof

const BASELINE_SOURCE: sview = __BASELINE_SOURCE__
const FALSE_INVARIANT_SOURCE: sview = __FALSE_INVARIANT_SOURCE__
const OVERRUN_SOURCE: sview = __OVERRUN_SOURCE__
const STALE_INITIALIZER_SOURCE: sview = __STALE_INITIALIZER_SOURCE__
const STALE_REBIND_SOURCE: sview = __STALE_REBIND_SOURCE__
const SHADOWED_PARAMETER_SOURCE: sview = __SHADOWED_PARAMETER_SOURCE__
const SHADOWED_GLOBAL_SOURCE: sview = __SHADOWED_GLOBAL_SOURCE__
const UNRELATED_INVARIANT_SOURCE: sview = __UNRELATED_INVARIANT_SOURCE__

def proof_test_parse_and_replay(source_text: sview, source: mutable darray[u8]&, report: mutable ProofReport&) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(source_text) |index, source_text, source|:
        source.push(sview_at(source_text, index))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    proof_check(file, report)
    proof_replay_certificates(report)

def proof_test_parse_declarations(source_text: sview, source: mutable darray[u8]&, report: mutable ProofReport&) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(source_text) |index, source_text, source|:
        source.push(sview_at(source_text, index))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    report.source_declarations <- file.top_decls

def proof_test_loop_goals(report: ProofReport&, function_name: sview, source_line: u32) -> (count: usize, all_replayed: bool):
    count: mutable usize = 0
    all_replayed: mutable bool = true
    for certificate in report.certificates |count, all_replayed, function_name, source_line|:
        if certificate.name == function_name and certificate.rule == "goal" and certificate.line == source_line:
            count <- count + 1
            all_replayed <- false if not certificate.replayed
    return (count, all_replayed)

def proof_test_has_loop_refusal(report: ProofReport&, function_name: sview, source_line: u32) -> bool:
    for finding in report.findings |function_name, source_line|:
        if finding.name == function_name and finding.line == source_line:
            return true if finding.kind == "invariant-unproven" or finding.kind == "invariant-not-preserved"
    return false

def main() -> i64 can Memory.Allocate, Abort.Panic:
    baseline_bytes: mutable darray[u8] = []
    baseline: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(BASELINE_SOURCE, &baseline_bytes, &baseline)
    bounded = proof_test_loop_goals(baseline, "bounded_counter", 9)
    return 101 if bounded.count != 2 or not bounded.all_replayed
    plain = proof_test_loop_goals(baseline, "countdown", 19)
    return 102 if plain.count == 0 or not plain.all_replayed

    init_index: mutable usize = baseline.fact_traces.count
    rebind_index: mutable usize = baseline.fact_traces.count
    for index in 0..<baseline.fact_traces.count |index, baseline, init_index, rebind_index|:
        trace: ProofFactTrace = baseline.fact_traces[index]
        continue if trace.kind != "local-binding" or trace.name != "bounded_counter"
        match trace.expression:
            Ast::Expr.Binary(Ast::Expr.Ident(name, _), TokenKind.EqEq, _, _):
                init_index <- index if name == "rounds" and trace.line == 8
                rebind_index <- index if name == "__elisa_rebind_0" and trace.line == 11
            _:
                pass
    return 103 if init_index >= baseline.fact_traces.count or rebind_index >= baseline.fact_traces.count
    baseline.replay_owner_line <- 6
    baseline.trace_owner_line <- 9
    return 104 if not proof_replay_fact_trace_entry(&baseline, init_index)
    return 105 if not proof_replay_fact_trace_entry(&baseline, rebind_index)

    # Altering only the trace site cannot preserve source provenance.
    init_original: ProofFactTrace = baseline.fact_traces[init_index]
    stale_trace: ProofFactTrace = ProofFactTrace{expression: init_original.expression, kernel_expression: init_original.kernel_expression, kind: init_original.kind, line: 11, name: init_original.name, dependency: init_original.dependency, premises_start: init_original.premises_start, premises_count: init_original.premises_count, kernel_premises_start: init_original.kernel_premises_start, kernel_premises_count: init_original.kernel_premises_count, summary_bindings_start: init_original.summary_bindings_start, summary_bindings_count: init_original.summary_bindings_count, summary_requires_start: init_original.summary_requires_start, summary_requires_count: init_original.summary_requires_count, summary_ensure_index: init_original.summary_ensure_index, owner_line: init_original.owner_line}
    baseline.fact_traces[init_index] <- stale_trace
    return 106 if proof_replay_fact_trace_entry(&baseline, init_index)
    baseline.fact_traces[init_index] <- init_original

    # The RHS and source location do not identify a rebind witness without its exact fresh
    # binding symbol. A different reserved pool entry must not be accepted for this assignment.
    rebind_original: ProofFactTrace = baseline.fact_traces[rebind_index]
    rebind_value: mutable Ast::Expr = Ast::Expr.Invalid
    match rebind_original.expression:
        Ast::Expr.Binary(_, TokenKind.EqEq, right, _):
            rebind_value <- right
        _:
            return 114
    rebind_position: Ast::Pos = Ast::expr_pos(rebind_original.expression)
    forged_rebind_expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("__elisa_rebind_63", rebind_position), TokenKind.EqEq, rebind_value, rebind_position)
    encoded_rebind: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_rebind_expression, &baseline, "bounded_counter")
    return 115 if not encoded_rebind.known
    forged_rebind_trace: ProofFactTrace = ProofFactTrace{expression: forged_rebind_expression, kernel_expression: encoded_rebind.root, kind: rebind_original.kind, line: rebind_original.line, name: rebind_original.name, dependency: rebind_original.dependency, premises_start: rebind_original.premises_start, premises_count: rebind_original.premises_count, kernel_premises_start: rebind_original.kernel_premises_start, kernel_premises_count: rebind_original.kernel_premises_count, summary_bindings_start: rebind_original.summary_bindings_start, summary_bindings_count: rebind_original.summary_bindings_count, summary_requires_start: rebind_original.summary_requires_start, summary_requires_count: rebind_original.summary_requires_count, summary_ensure_index: rebind_original.summary_ensure_index, owner_line: rebind_original.owner_line}
    baseline.fact_traces.push(forged_rebind_trace)
    return 116 if proof_replay_fact_trace_entry(&baseline, baseline.fact_traces.count - 1)

    # The old RHS witness is invalid once the actual source assignment changes.
    stale_rebind_bytes: mutable darray[u8] = []
    stale_rebind_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(STALE_REBIND_SOURCE, &stale_rebind_bytes, &stale_rebind_report)
    baseline.source_declarations <- stale_rebind_report.source_declarations
    return 117 if proof_replay_fact_trace_entry(&baseline, rebind_index)

    # A same-spelled parameter or global constant would make the kernel identifier's binding
    # ambiguous even though a local declaration and assignment occur at the expected lines.
    shadowed_parameter_bytes: mutable darray[u8] = []
    shadowed_parameter_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_declarations(SHADOWED_PARAMETER_SOURCE, &shadowed_parameter_bytes, &shadowed_parameter_report)
    baseline.source_declarations <- shadowed_parameter_report.source_declarations
    return 118 if proof_replay_fact_trace_entry(&baseline, init_index) or proof_replay_fact_trace_entry(&baseline, rebind_index)
    shadowed_global_bytes: mutable darray[u8] = []
    shadowed_global_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_declarations(SHADOWED_GLOBAL_SOURCE, &shadowed_global_bytes, &shadowed_global_report)
    baseline.source_declarations <- shadowed_global_report.source_declarations
    return 119 if proof_replay_fact_trace_entry(&baseline, init_index) or proof_replay_fact_trace_entry(&baseline, rebind_index)

    # A forged equality at the right line is not the source initializer.
    forged_position: Ast::Pos = Ast::expr_pos(init_original.expression)
    forged_expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident("rounds", forged_position), TokenKind.EqEq, Ast::Expr.IntLit(987654321, forged_position), forged_position)
    encoded: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_expression, &baseline, "bounded_counter")
    return 107 if not encoded.known
    forged_trace: ProofFactTrace = ProofFactTrace{expression: forged_expression, kernel_expression: encoded.root, kind: init_original.kind, line: init_original.line, name: init_original.name, dependency: init_original.dependency, premises_start: init_original.premises_start, premises_count: init_original.premises_count, kernel_premises_start: init_original.kernel_premises_start, kernel_premises_count: init_original.kernel_premises_count, summary_bindings_start: init_original.summary_bindings_start, summary_bindings_count: init_original.summary_bindings_count, summary_requires_start: init_original.summary_requires_start, summary_requires_count: init_original.summary_requires_count, summary_ensure_index: init_original.summary_ensure_index, owner_line: init_original.owner_line}
    baseline.fact_traces.push(forged_trace)
    return 108 if proof_replay_fact_trace_entry(&baseline, baseline.fact_traces.count - 1)

    # Old initializer evidence must not transfer to changed source at the same binding site.
    stale_bytes: mutable darray[u8] = []
    stale_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(STALE_INITIALIZER_SOURCE, &stale_bytes, &stale_report)
    baseline.source_declarations <- stale_report.source_declarations
    return 109 if proof_replay_fact_trace_entry(&baseline, init_index)

    # An unrelated invariant on the same consumer line cannot stand in for the source contract.
    unrelated_bytes: mutable darray[u8] = []
    unrelated_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(UNRELATED_INVARIANT_SOURCE, &unrelated_bytes, &unrelated_report)
    baseline.source_declarations <- unrelated_report.source_declarations
    return 110 if proof_replay_fact_trace_entry(&baseline, init_index)

    false_bytes: mutable darray[u8] = []
    false_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(FALSE_INVARIANT_SOURCE, &false_bytes, &false_report)
    return 111 if not proof_test_has_loop_refusal(false_report, "bounded_counter", 9)

    overrun_bytes: mutable darray[u8] = []
    overrun_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(OVERRUN_SOURCE, &overrun_bytes, &overrun_report)
    return 112 if not proof_test_has_loop_refusal(overrun_report, "bounded_counter", 9)

    # Fresh parsing and independent replay must reproduce both loop obligations.
    fresh_bytes: mutable darray[u8] = []
    fresh_report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(BASELINE_SOURCE, &fresh_bytes, &fresh_report)
    fresh = proof_test_loop_goals(fresh_report, "bounded_counter", 9)
    return 113 if fresh.count != 2 or not fresh.all_replayed
    return 0
'''


def prove(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return result.returncode, json.loads(result.stdout)


status, data = prove(FIXTURE)
assert status in (0, 1) and data["status"] in ("proved", "proved_with_replay_gaps") and data["findings"] == [], data
fixture_status = data["status"]
fixture_replay = data["replay"]
if data["status"] == "proved":
    assert data["replay"]["gaps"] == 0, data["replay"]
else:
    # This focused regression does not claim whole-fixture proof while unrelated replay gaps
    # exist; the two target certificates are checked individually below.
    assert data["replay"]["gaps"] > 0, data["replay"]
bounded_loop_certificates = [
    certificate for certificate in data["certificates"]
    if certificate["name"] == "bounded_counter" and certificate["rule"] == "goal" and certificate["line"] == 9
]
assert len(bounded_loop_certificates) == 2, bounded_loop_certificates
assert all(certificate["replayed"] for certificate in bounded_loop_certificates), bounded_loop_certificates

source = FIXTURE.read_text()
lines = source.split("\n")
invariant_lines = [index for index, line in enumerate(lines) if line.strip().startswith("invariant ")]
assert len(invariant_lines) == 4, invariant_lines
with tempfile.TemporaryDirectory() as scratch:
    mutants = 0
    for index in invariant_lines:
        indent, claim = lines[index].split("invariant ", 1)
        variants = [f"not ({claim})"]
        if ">=" in claim:
            variants.append(claim.replace(">=", ">", 1))
        if "<=" in claim:
            variants.append(claim.replace("<=", "<", 1))
        for variant in variants:
            mutated = list(lines)
            mutated[index] = f"{indent}invariant {variant}"
            path = Path(scratch) / f"mutant_{mutants}.elisa"
            path.write_text("\n".join(mutated))
            status, data = prove(path)
            assert status != 0 and data["status"] != "proved", (index + 1, variant, data["status"])
            mutants += 1
    assert mutants == 8, mutants

    if not COMPILER:
        sys.exit("loop invariants compile: ELISA_COMPILER_BIN is not set")
    obj = Path(scratch) / "loops.o"
    exe = Path(scratch) / "loops"
    built = subprocess.run([COMPILER, "-permissive", "-emit", "obj", "-O0", "-o", str(obj), str(FIXTURE)], capture_output=True, text=True, timeout=600)
    assert built.returncode == 0 and obj.exists(), built.stderr
    symbols = subprocess.run(["nm", str(obj)], capture_output=True, text=True).stdout
    for name in ("bounded_counter", "countdown", "count_up", "stop_early"):
        assert re.search(rf"\b_?{name}\b", symbols), f"{name} was not emitted"
    linked = subprocess.run(["cc", "-o", str(exe), str(obj)], capture_output=True, text=True)
    assert linked.returncode == 0, linked.stderr
    ran = subprocess.run([str(exe)], timeout=60)
    assert ran.returncode == 0, ran.returncode


def run_source_binding_replay_harness():
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not STAGE1_FRESHNESS.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    if not PINNED_FRONTEND_ROOT.is_dir() or not (PINNED_FRONTEND_ROOT / ".rev").is_file():
        raise SystemExit(f"pinned frontend snapshot is missing: {PINNED_FRONTEND_ROOT}; build the proof project first")
    snapshot_revision = (PINNED_FRONTEND_ROOT / ".rev").read_text().strip()
    if snapshot_revision != PINNED_FRONTEND_REV:
        raise SystemExit(
            f"pinned frontend snapshot mismatch: snapshot={snapshot_revision} expected={PINNED_FRONTEND_REV}"
        )
    freshness = subprocess.run(
        ["bash", str(STAGE1_FRESHNESS), str(STAGE1)], capture_output=True, text=True, cwd=COMPILER_ROOT
    )
    if freshness.returncode:
        raise AssertionError(f"Stage1 freshness check failed:\n{freshness.stdout}\n{freshness.stderr}")
    baseline_source = FIXTURE.read_text()
    sources = {
        "__BASELINE_SOURCE__": baseline_source,
        "__FALSE_INVARIANT_SOURCE__": baseline_source.replace("invariant rounds <= limit", "invariant rounds < limit", 1),
        "__OVERRUN_SOURCE__": baseline_source.replace("rounds <- rounds + 1", "rounds <- rounds + 2", 1),
        "__STALE_INITIALIZER_SOURCE__": baseline_source.replace(
            "rounds: mutable usize = 0\n    while rounds < limit",
            "rounds: mutable usize = 4\n    while rounds < limit",
            1,
        ),
        "__STALE_REBIND_SOURCE__": baseline_source.replace("rounds <- rounds + 1", "rounds <- rounds + 2", 1),
        "__SHADOWED_PARAMETER_SOURCE__": baseline_source.replace(
            "def bounded_counter(limit: usize)", "def bounded_counter(rounds: usize, limit: usize)", 1
        ),
        "__SHADOWED_GLOBAL_SOURCE__": baseline_source.replace(
            "# A while loop with a counter bounded by a parameter.", "const rounds: usize = 99", 1
        ),
        "__UNRELATED_INVARIANT_SOURCE__": baseline_source.replace("invariant rounds <= limit", "invariant rounds < limit", 1),
    }
    assert all(source != baseline_source for marker, source in sources.items() if marker != "__BASELINE_SOURCE__")
    harness = REPLAY_HARNESS
    for marker, source in sources.items():
        harness = harness.replace(marker, json.dumps(source))

    with tempfile.TemporaryDirectory(prefix="bounded-counter-source-replay-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source_path = directory / "bounded_counter_source_replay.elisa"
        executable = directory / "bounded_counter_source_replay"
        harness = harness.replace("../../Elisa-compiler/", str(PINNED_FRONTEND_ROOT.resolve()) + "/").replace(
            'include "../src/', 'include "../../src/'
        )
        source_path.write_text(harness, encoding="utf-8")
        compiled = subprocess.run(
            [str(STAGE1_WRAPPER), "-emit", "exe", "-O0", "-o", str(executable), str(source_path)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=600,
        )
        if compiled.returncode:
            raise AssertionError(f"fresh Stage1 source-binding harness failed:\n{compiled.stdout}\n{compiled.stderr}")
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    return freshness.stdout.strip()


provenance = run_source_binding_replay_harness()
print(
    f"loop invariants: targeted source-bound replay controls passed; fixture={fixture_status} "
    f"({fixture_replay['gaps']} unrelated replay gaps); {provenance}; pinned frontend {PINNED_FRONTEND_REV}"
)
