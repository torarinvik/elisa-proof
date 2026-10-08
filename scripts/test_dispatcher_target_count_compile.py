"""Count distinct resolved targets for the existing bounded dispatcher policy."""
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(os.environ.get('ELISA_COMPILER_ROOT', ROOT.parent / 'Elisa-compiler')).resolve()
FRONTEND = Path(os.environ.get('ELISA_PROOF_FRONTEND_ROOT', ROOT / 'build/snapshot/Elisa-compiler')).resolve()
module = ast.parse((ROOT / 'scripts/test_loop_invariants_compile.py').read_text())
template = next(ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'REPLAY_HARNESS' for target in node.targets))
prefix = template.split('extend ElisaProof:', 1)[0]
prefix = prefix.replace('../../Elisa-compiler/', str(FRONTEND) + '/').replace('../src/', str(ROOT / 'src') + '/')
harness = prefix + r'''extend ElisaProof:
    public:
        def target_count_gate() -> i64:
            table: mutable ProofFunctionTable = proof_empty_functions()
            table.names <- ["a", "b", "c", "d", "e", "caller"]
            table.call_starts <- [0, 0, 0, 0, 0, 0]
            table.call_counts <- [0, 0, 0, 0, 0, 24]
            for _ in 0..<24 |table|:
                table.all_call_targets.push(0)
            return 1 if proof_return_analysis_call_target_count(table, 5) != 1
            return 2 if proof_return_analysis_fact_state_budget("caller", 24, 1, proof_return_analysis_call_target_count(table, 5), 24) != 128
            table.all_call_targets[1] <- 1
            table.all_call_targets[2] <- 2
            table.all_call_targets[3] <- 3
            return 3 if proof_return_analysis_call_target_count(table, 5) != 4
            table.all_call_targets[4] <- 4
            return 4 if proof_return_analysis_call_target_count(table, 5) != 5
            return 5 if proof_return_analysis_fact_state_budget("caller", 24, 1, proof_return_analysis_call_target_count(table, 5), 24) != 64
            table.all_call_targets[4] <- 0
            table.all_call_targets[0] <- 6
            return 6 if proof_return_analysis_call_target_count(table, 5) != 5
            table.all_call_targets[0] <- 0
            table.call_starts[5] <- 18446744073709551615
            return 7 if proof_return_analysis_call_target_count(table, 5) != 5
            table.call_starts[5] <- 0
            table.call_counts[5] <- 25
            return 8 if proof_return_analysis_call_target_count(table, 5) != 5
            table.call_counts[5] <- 0
            return 9 if proof_return_analysis_call_target_count(table, 5) != 0
            return 10 if proof_return_analysis_call_target_count(table, 6) != 5
            table.call_counts[5] <- 193
            return 11 if proof_return_analysis_call_target_count(table, 5) != 5
            return 12 if proof_return_analysis_fact_state_budget("caller", 28, 1, 1, 11) != 64
            return 13 if proof_return_analysis_fact_state_budget("caller", 28, 1, 1, 12) != 128
            return 14 if proof_return_analysis_fact_state_budget("caller", 29, 1, 1, 25) != 64
            return 15 if proof_return_analysis_fact_state_budget("caller", 28, 1, 0, 24) != 64
            0

        def summary_gate(text: sview, positive: bool) -> i64:
            bytes: mutable darray[u8] = []
            for index in 0..<sview_len(text) |bytes|:
                bytes.push(sview_at(text, index))
            bytes.push(0)
            file: Ast::File = frontend_parse(&bytes[0])
            report: mutable ProofReport = proof_empty_report()
            proof_check(file, &report)
            proof_replay_certificates(&report)
            return 30 if report.replay_gaps != 0
            if positive:
                return 31 if report.findings.count != 0 or report.proven != report.obligations
            else:
                return 32 if report.proven == report.obligations
                found: mutable bool = false
                for finding in report.findings |found|:
                    found <- true if finding.kind == "ensure-unproven" and finding.name == "rejected_wrapper_status"
                return 33 if not found
            0

        def dispatcher_gate(text: sview, positive: bool) -> i64:
            bytes: mutable darray[u8] = []
            for index in 0..<sview_len(text) |bytes|:
                bytes.push(sview_at(text, index))
            bytes.push(0)
            file: Ast::File = frontend_parse(&bytes[0])
            report: mutable ProofReport = proof_empty_report()
            proof_check(file, &report)
            proof_replay_certificates(&report)
            return 20 if report.replay_gaps != 0
            return 21 if positive and report.findings.count != 0
            if positive:
                return 22 if report.proven != report.obligations
            else:
                return 24 if report.findings.count != 1
                return 25 if report.proven == report.obligations
                found: mutable bool = false
                for finding in report.findings |found|:
                    found <- true if finding.kind == "control-flow-analysis-budget" and finding.name == "dispatch_too_long"
                return 23 if not found
            0

def main() -> i64:
    direct: i64 = target_count_gate()
    return direct if direct != 0
    positive: i64 = dispatcher_gate(__POSITIVE__, true)
    return positive if positive != 0
    negative: i64 = dispatcher_gate(__NEGATIVE__, false)
    return negative if negative != 0
    summary: i64 = summary_gate(__SUMMARY__, true)
    return summary if summary != 0
    cast: i64 = summary_gate(__CAST__, true)
    return cast if cast != 0
    summary_gate(__SUMMARY_NEGATIVE__, false)
'''
harness = harness.replace('__POSITIVE__', json.dumps((ROOT / 'examples/dispatcher_budget.elisa').read_text()))
harness = harness.replace('__NEGATIVE__', json.dumps((ROOT / 'examples/rejected_dispatcher_budget.elisa').read_text()))
summary_source = (ROOT / 'examples/compact_mutating_call_summary.elisa').read_text()
summary_negative = (ROOT / 'examples/rejected_compact_mutating_call_summary.elisa').read_text().replace(
    'include "compact_mutating_call_summary.elisa"', summary_source)
harness = harness.replace('__SUMMARY__', json.dumps(summary_source))
harness = harness.replace('__SUMMARY_NEGATIVE__', json.dumps(summary_negative))
harness = harness.replace('__CAST__', json.dumps((ROOT / 'examples/extend_mut_ref_fact_across_cast.elisa').read_text()))
with tempfile.TemporaryDirectory(prefix='dispatcher-target-count-') as temporary:
    path = Path(temporary) / 'main.elisa'
    binary = Path(temporary) / 'gate'
    path.write_text(harness)
    subprocess.run([str(COMPILER / 'scripts/elisac_stage1.sh'), str(path), '-emit', 'exe', '-O0', '-o', str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print('dispatcher targets: repeated identities deduplicated; malformed/opaque/wide sets refused; original window retained')
