"""Compile independent loop-entry initializer reconstruction and refusal controls."""
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")).resolve()
FRONTEND = ROOT / "build/snapshot/Elisa-compiler"
module = ast.parse((ROOT / "scripts/test_loop_invariants_compile.py").read_text())
template = next(ast.literal_eval(node.value) for node in module.body
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "REPLAY_HARNESS" for t in node.targets))
prefix = template.split("extend ElisaProof:", 1)[0]
prefix = prefix.replace("../../Elisa-compiler/", str(FRONTEND.resolve()) + "/")
prefix = prefix.replace("../src/", str(ROOT / "src") + "/")
source = 'def bubble_pass(xs: mutable darray[i64]&, n: usize) -> i64:\n    requires 0 < n and n <= xs.count\n    ensures forall i in 0..<n: xs[i] <= result\n    k: mutable usize = 0\n    m: mutable i64 = xs[0]\n    while k + 1 < n:\n        invariant k < n\n        invariant m == xs[k]\n        invariant forall i in 0..<k: xs[i] <= m\n        if xs[k + 1] < m:\n            xs[k] <- xs[k + 1]\n            xs[k + 1] <- m\n        else:\n            m <- xs[k + 1]\n        k <- k + 1\n    return m\n'
harness = prefix + r'''
extend ElisaProof:
    public:
        def expanded_gate(report: mutable ProofReport&, trace: ProofFactTrace, certificate: ProofGoalCertificate) -> bool:
            report.replay_owner_line <- 1
            report.trace_owner_line <- 6
            body: mutable darray[Ast::Stmt] = []
            return false if not proof_replay_source_owner_body(report, trace.name, 1, &body)
            invariants: mutable darray[Ast::Expr] = []
            loops: mutable usize = 0
            proof_replay_loop_entry_invariants(body, 6, &invariants, &loops, false)
            return false if loops != 1
            for invariant in invariants |report, trace, certificate, body|:
                return true if proof_replay_loop_entry_expanded_goal(report, trace, certificate, body, invariant)
            false

        def prepare(report: mutable ProofReport&) -> void:
            proof_replay_build_fact_trace_index(report)
            proof_replay_cache_fact_origins(report)
            report.replay_owner_line <- 1
            report.trace_owner_line <- 6

        def entry_gate(report: ProofReport&, trace: ProofFactTrace) -> bool:
            proof_replay_loop_entry_certificate(report, trace)

def parse_source(text: sview, bytes: mutable darray[u8]&, report: mutable ProofReport&) -> void:
    bytes.clear()
    for index in 0..<sview_len(text) |bytes|:
        bytes.push(sview_at(text, index))
    bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    proof_check(file, report)

def main() -> i64:
    bytes: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    parse_source(__SOURCE__, &bytes, &report)
    prepare(&report)
    preservation_seen: mutable bool = false
    for index in 0..<report.certificates.count |report, preservation_seen|:
        certificate: ProofGoalCertificate = report.certificates[index]
        continue if certificate.name != "bubble_pass" or certificate.line != 6
        report.trace_consumer_certificate_index <- index + 1
        for offset in 0..<certificate.facts_count |report, certificate, preservation_seen|:
            trace_index: usize = report.traces.origin_indices[certificate.facts_start + offset]
            continue if trace_index >= report.traces.records.count
            trace: ProofFactTrace = report.traces.records[trace_index]
            continue if trace.line != 6 or (trace.kind != "loop-condition" and trace.kind != "loop-invariant" and trace.kind != "loop-range")
            preservation_seen <- true
            return 4 if entry_gate(&report, trace)
    return 5 if not preservation_seen
    for index in 0..<report.certificates.count |report, bytes|:
        certificate: ProofGoalCertificate = report.certificates[index]
        continue if certificate.name != "bubble_pass" or certificate.line != 6
        match certificate.goal:
            Ast::Expr.Binary(_, TokenKind.EqEq, _, _):
                pass
            _:
                continue
        report.trace_consumer_certificate_index <- index + 1
        for offset in 0..<certificate.facts_count |report, certificate, bytes|:
            trace_index: usize = report.traces.origin_indices[certificate.facts_start + offset]
            return 1 if trace_index >= report.traces.records.count
            trace: ProofFactTrace = report.traces.records[trace_index]
            continue if trace.kind != "local-binding"
            return 2 if not expanded_gate(&report, trace, certificate)
            return 3 if not proof_replay_fact_trace_entry(&report, trace_index)
            __CONTROLS__
            return 0
    return 99
'''
controls = {
    "changed_initializer": source.replace("m: mutable i64 = xs[0]", "m: mutable i64 = xs[1]"),
    "pre_write": source.replace("    ensures forall i in 0..<n: xs[i] <= result", "    xs[0] <- 9"),
    "effectful_prefix": source.replace("    ensures forall i in 0..<n: xs[i] <= result", "    touch(xs)"),
    "shadow_receiver": source.replace("m: mutable i64 = xs[0]", "xs: mutable i64 = xs[0]"),
    "element_mismatch": source.replace("m: mutable i64", "m: mutable i32"),
    "reference_local": source.replace("m: mutable i64", "m: mutable i64&"),
    "primitive_alias": source + "\ntype i64 = u64\n",
    "nonliteral_index": source.replace("m: mutable i64 = xs[0]", "m: mutable i64 = xs[n]"),
    "moved_header": source.replace("    while k + 1 < n:", "\n    while k + 1 < n:"),
    "duplicate_local": source.replace("    ensures forall i in 0..<n: xs[i] <= result", "    m: mutable i64 = xs[0]"),
    "unrelated_effectful_initializer": source.replace("    ensures forall i in 0..<n: xs[i] <= result", "    other: i64 = touch(xs)"),
}
lines = []
for index, (name, text) in enumerate(controls.items(), 10):
    lines += [f"other_{index}: mutable ProofReport = proof_empty_report()",
              f"parse_source({json.dumps(text)}, &bytes, &other_{index})",
              f"return {index} if expanded_gate(&other_{index}, trace, certificate)"]
harness = harness.replace("__SOURCE__", json.dumps(source)).replace("__CONTROLS__", "\n            ".join(lines))
with tempfile.TemporaryDirectory(prefix="loop-entry-source-controls-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print("loop entry: original binding independently replays; preservation and 11 forged source controls refused")
