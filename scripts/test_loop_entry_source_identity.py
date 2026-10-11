"""Check loop source identity and reject certificates relabeled with unknown phases."""
import ast
import os
from pathlib import Path
from source_binding_harness_support import run_source_binding_replay_harness

ROOT = Path(__file__).resolve().parents[1]
module = ast.parse((ROOT / "scripts/test_loop_invariants_compile.py").read_text())
harness = next(ast.literal_eval(node.value) for node in module.body
               if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == "REPLAY_HARNESS"
                       for target in node.targets))
phase_probe = r'''
extend ElisaProof:
    public:
        def proof_test_unknown_certificate_phase_rejected(report: mutable ProofReport&) -> bool:
            for certificate_index in 0..<report.certificates.count |report, certificate_index|:
                certificate: ProofGoalCertificate = report.certificates[certificate_index]
                continue if certificate.source_phase != "loop-invariant-preservation"
                for attempt_index in 0..<report.goal_attempts.count |report, certificate_index, attempt_index, certificate|:
                    attempt: ProofGoalAttempt = report.goal_attempts[attempt_index]
                    continue if not attempt.has_certificate or attempt.certificate_index != certificate_index
                    return false if not proof_replay_attempt_matches_certificate(report, attempt, certificate, certificate_index)
                    old_phase: sview = certificate.source_phase
                    report.certificates[certificate_index].source_phase <- "unrecognized-phase"
                    report.goal_attempts[attempt_index].source_phase <- "unrecognized-phase"
                    changed_attempt: ProofGoalAttempt = report.goal_attempts[attempt_index]
                    changed_certificate: ProofGoalCertificate = report.certificates[certificate_index]
                    rejected: bool = not proof_replay_attempt_matches_certificate(report, changed_attempt, changed_certificate, certificate_index)
                    report.certificates[certificate_index].source_phase <- old_phase
                    report.goal_attempts[attempt_index].source_phase <- old_phase
                    return rejected
            return false
'''
harness = harness.replace("def main()", phase_probe + "\ndef main()", 1)
harness = harness.split("    false_bytes: mutable darray[u8] = []")[0]
harness += "    return 201 if not ElisaProof::proof_test_unknown_certificate_phase_rejected(&baseline)\n    return 0\n"
run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Loop source identity and certificate phase controls passed")
