"""Direct proof APIs must reject mandatory semantic errors before certificate construction."""
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
valid = "def checked() -> bool:\n    ensure result == true\n    true\n"
invalid = (
    valid + "\ndef missing_name() -> bool:\n    ensure result == true\n    undefined_value\n",
    valid + "\ndef missing_type(value: MissingType) -> bool:\n    ensure result == true\n    true\n",
    valid + "\ndef checked() -> bool:\n    ensure result == true\n    true\n",
)
invalid += tuple(valid + "\n" + source for source in (
    "def trap(raw: i64) -> i64:\n    return raw / 0\n",
    "def trap(raw: i64) -> i64:\n    return raw % 0\n",
    "def trap() -> i64:\n    value: i64 = 1\n    return value << 64\n",
    "def trap() -> i64:\n    value: i64 = 1\n    return value << -2\n",
))
constants = "const VALID_API_SOURCE: sview = " + json.dumps(valid) + "\n"
constants += "const REFINEMENT_API_SOURCE: sview = " + json.dumps('type Positive = i64 where self >= 0\ndef checked(value: Positive) -> i64:\n    ensure result >= 0\n    return value\n') + "\n"
constants += "const MUTUAL_API_SOURCE: sview = " + json.dumps((ROOT / "examples/mutual_structural_decreases.elisa").read_text().replace("structural_even", "checked")) + "\n"
constants += "const UNKNOWN_API_SOURCE: sview = " + json.dumps("def checked(value: bool) -> bool:\n    ensure result == true\n    value\n") + "\n"
constants += "const INVALID_API_SOURCES: sview[7] = [" + ", ".join(map(json.dumps, invalid)) + "]\n"
harness = prefix + constants + r'''
def api_probe(text: sview, source: mutable darray[u8]&, report: mutable ProofReport&, diagnostics: mutable darray[Semantic::Diagnostic]&, route: usize) -> void can Memory.Allocate, Abort.Panic:
    source.clear()
    for index in 0..<sview_len(text) |index, text, source|:
        source.push(sview_at(text, index))
    source.push(0)
    file: mutable Ast::File = frontend_parse(&source[0])
    # Match the CLI's source-owned refinement preparation before calling the core API.
    refusals: mutable ProofReport = proof_empty_report()
    refined: mutable darray[sview] = []
    proof_add_refinement_signature_contracts(&file, &refusals, &refined)
    diagnostics.clear()
    if route == 0:
        proof_check(file, report)
    elif route == 1:
        proof_check_with_semantic_diagnostics(file, report, diagnostics)
    else:
        proof_check_focused_with_semantic_diagnostics(file, report, diagnostics, "checked")
    proof_replay_certificates(report)

def main() -> i64 can Memory.Allocate, Abort.Panic:
    source: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    diagnostics: mutable darray[Semantic::Diagnostic] = []
    for route in 0..<3 |route, source, report, diagnostics|:
        for index in 0..<7 |index, route, source, report, diagnostics|:
            api_probe(VALID_API_SOURCE, &source, &report, &diagnostics, route)
            return 170 if report.certificates.count == 0 or report.proven == 0
            api_probe(INVALID_API_SOURCES[index], &source, &report, &diagnostics, route)
            return 171 if report.certificates.count != 0 or report.goal_attempts.count != 0 or report.proven != 0
            return 172 if report.source_declarations.count != 0 or report.traces.records.count != 0 or report.kernel.nodes.count != 0
            expected_kind: sview = "semantic-source-inadmissible" if index < 3 else "arithmetic-safety-refuted"
            return 173 if not any finding in report.findings where finding.kind == expected_kind
            if route != 0 and index < 3:
                return 174 if not any diagnostic in diagnostics where Semantic::diagnostic_severity(diagnostic) == 1
        api_probe(VALID_API_SOURCE, &source, &report, &diagnostics, route)
        return 175 if report.certificates.count == 0 or report.failed != 0 or report.replay_gaps != 0
        api_probe(REFINEMENT_API_SOURCE, &source, &report, &diagnostics, route)
        return 190 if report.certificates.count == 0
        return 191 if report.proven == 0
        return 192 if report.failed != 0
        return 193 if report.replay_gaps != 0
        api_probe(MUTUAL_API_SOURCE, &source, &report, &diagnostics, route)
        return 177 if report.failed != 0 or report.structural.verified_names.count == 0 or report.replay_gaps != 0
        api_probe(UNKNOWN_API_SOURCE, &source, &report, &diagnostics, route)
        return 178 if report.failed == 0 and report.proven == report.obligations
    return 0
'''
run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Direct API semantic admission: mandatory errors clear proof state on all three routes; valid reuse replays")
