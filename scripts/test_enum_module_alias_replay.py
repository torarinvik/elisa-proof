"""Imported-module enum witnesses must refuse a source alias target changed after checking."""

import ast
import os
from pathlib import Path

from source_binding_harness_support import run_source_binding_replay_harness


ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler"))
PIN = (ROOT / "ELISA_COMPILER_REV").read_text(encoding="ascii").strip()
tree = ast.parse((ROOT / "scripts/test_loop_invariants_compile.py").read_text(encoding="utf-8"))
template = next(
    ast.literal_eval(node.value)
    for node in tree.body
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "REPLAY_HARNESS" for target in node.targets)
)
harness = template.split("def main()", 1)[0] + r'''
def main() -> i64 can Memory.Allocate, Abort.Panic:
    source: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(BASELINE_SOURCE, &source, &report)
    return 1 if report.failed != 0 or report.replay_gaps != 0

    target_row: mutable usize = report.source.source_annotations.count
    original_target: mutable sview = ""
    for index in 0..<report.source.source_annotations.count |index, report, target_row, original_target|:
        annotation: Ast::EnumAnnotation = report.source.source_annotations[index]
        if annotation.name == "__using_alias_target" and annotation.owner == "ScopedAlias":
            target_row <- index
            original_target <- annotation.owner
    return 2 if target_row >= report.source.source_annotations.count or original_target != "ScopedAlias"

    # The report's parsed import mapping is mutable state. Changing it after certificate
    # construction must invalidate replay instead of reusing the old enum witness.
    report.source.source_annotations[target_row].owner <- "TamperedModule"
    proof_replay_certificates(&report)
    return 3 if report.replay_gaps == 0

    report.source.source_annotations[target_row].owner <- original_target
    proof_replay_certificates(&report)
    return 4 if report.replay_gaps != 0
    return 0
'''

run_source_binding_replay_harness(
    ROOT,
    ROOT / "examples/enum_alias_precedence.elisa",
    COMPILER,
    PIN,
    harness,
)
print("enum import replay: valid alias target replays; post-check target tampering refuses; restored mapping replays")
