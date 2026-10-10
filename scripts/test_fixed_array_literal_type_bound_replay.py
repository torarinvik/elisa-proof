"""Authenticate fixed-array literal-index bounds through the direct proof API."""
import ast
import json
import os
from pathlib import Path
from source_binding_harness_support import run_source_binding_replay_harness

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / "scripts/test_loop_invariants_compile.py").read_text())
prefix = next(ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == "REPLAY_HARNESS"
                      for target in node.targets)).split("def main()")[0]
fixture_source = (ROOT / "examples/fixed_array_constant_indices.elisa").read_text()
constants = "const FIXED_ARRAY_LITERAL_SOURCE: sview = " + json.dumps(fixture_source) + "\n"
parenthesized_source = fixture_source.replace("return values[1]", "return (values)[1]", 1)
nested_source = fixture_source.replace("return values[1]", "return [values[1]][0]", 1)
constants += "const PARENTHESIZED_ARRAY_LITERAL_SOURCE: sview = " + json.dumps(parenthesized_source) + "\n"
constants += "const NESTED_ARRAY_LITERAL_SOURCE: sview = " + json.dumps(nested_source) + "\n"
harness = prefix + constants + r'''
def api_probe(text: sview, source: mutable darray[u8]&, report: mutable ProofReport&, diagnostics: mutable darray[Semantic::Diagnostic]&) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: mutable Ast::File = (frontend_parse(&source[0]) can Global{Read,Write})
    refusals: mutable ProofReport = proof_empty_report()
    refined: mutable darray[sview] = []
    proof_add_refinement_signature_contracts(&file, &refusals, &refined)
    diagnostics.clear()
    (proof_check_with_semantic_diagnostics(file, report, diagnostics) can Global{Read,Write})
    (proof_replay_certificates(report) can Global{Read,Write})

def main() -> i64 can Memory.Allocate, Abort.Panic:
    source: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    diagnostics: mutable darray[Semantic::Diagnostic] = []
    (api_probe(FIXED_ARRAY_LITERAL_SOURCE, &source, &report, &diagnostics) can Global{Read,Write})
    return 240 if report.failed != 0 or report.replay_gaps != 0 or report.proven != report.obligations
    position: Ast::Pos = Ast::pos_at_line(8)
    genuine_expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.IntLit(1, position), TokenKind.Lt, Ast::Expr.Field(Ast::Expr.Ident("values", position), "count", position), position)
    genuine_index: mutable usize = report.traces.records.count
    for index in 0..<report.traces.records.count |index, report, genuine_expression, genuine_index|:
        trace: ProofFactTrace = report.traces.records[index]
        if trace.kind == "type-bound" and trace.line == 8 and trace.name == "fixed_literal_index_after_unsigned_facts" and proof_replay_expr_equal(trace.expression, genuine_expression):
            genuine_index <- index
            break
    return 241 if genuine_index >= report.traces.records.count
    return 242 if not (proof_replay_fact_trace_entry(&report, genuine_index) can Global{Read,Write})
    original: ProofFactTrace = report.traces.records[genuine_index]
    forged_expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.IntLit(2, position), TokenKind.Lt, Ast::Expr.Field(Ast::Expr.Ident("values", position), "count", position), position)
    forged_encoding: (known: bool, root: usize) = proof_kernel_encode_annotated_checked(forged_expression, &report, "fixed_literal_index_after_unsigned_facts")
    return 243 if not forged_encoding.known
    report.traces.records[genuine_index] <- ProofFactTrace{expression: forged_expression, kernel_expression: forged_encoding.root, kind: original.kind, line: original.line, name: original.name, dependency: original.dependency, premises_start: original.premises_start, premises_count: original.premises_count, kernel_premises_start: original.kernel_premises_start, kernel_premises_count: original.kernel_premises_count, summary_bindings_start: original.summary_bindings_start, summary_bindings_count: original.summary_bindings_count, summary_requires_start: original.summary_requires_start, summary_requires_count: original.summary_requires_count, summary_ensure_index: original.summary_ensure_index, owner_line: original.owner_line}
    forged_replayed: bool = (proof_replay_fact_trace_entry(&report, genuine_index) can Global{Read,Write})
    report.traces.records[genuine_index] <- original
    return 244 if forged_replayed
    return 245 if not (proof_replay_fact_trace_entry(&report, genuine_index) can Global{Read,Write})
    parenthesized_report: mutable ProofReport = proof_empty_report()
    parenthesized_diagnostics: mutable darray[Semantic::Diagnostic] = []
    (api_probe(PARENTHESIZED_ARRAY_LITERAL_SOURCE, &source, &parenthesized_report, &parenthesized_diagnostics) can Global{Read,Write})
    return 246 if parenthesized_report.failed != 0 or parenthesized_report.replay_gaps != 0 or parenthesized_report.proven != parenthesized_report.obligations
    nested_report: mutable ProofReport = proof_empty_report()
    nested_diagnostics: mutable darray[Semantic::Diagnostic] = []
    (api_probe(NESTED_ARRAY_LITERAL_SOURCE, &source, &nested_report, &nested_diagnostics) can Global{Read,Write})
    return 247 if nested_report.failed != 0 or nested_report.replay_gaps != 0 or nested_report.proven != nested_report.obligations
    return 0
'''

run_source_binding_replay_harness(
    ROOT,
    ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(),
    harness,
)
print("Fixed-array literal replay: direct API authenticates direct, parenthesized and nested values[1] uses, and rejects a forged 2 bound")
