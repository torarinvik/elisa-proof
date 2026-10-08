"""Compile literal-array count denial replay and its narrow classification controls."""
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")).resolve()
FRONTEND = Path(os.environ.get("ELISA_PROOF_FRONTEND_ROOT", ROOT / "build/snapshot/Elisa-compiler")).resolve()
module = ast.parse((ROOT / "scripts/test_loop_invariants_compile.py").read_text())
template = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "REPLAY_HARNESS" for t in n.targets))
prefix = template.split("extend ElisaProof:", 1)[0]
prefix = prefix.replace("../../Elisa-compiler/", str(FRONTEND) + "/").replace("../src/", str(ROOT / "src") + "/")
harness = prefix + r'''
extend ElisaProofKernelReplay:
    public:
        def count_controls() -> i64:
            nodes: mutable darray[ElisaProofKernelCore::ProofKernelNode] = []
            children: mutable darray[usize] = []
            facts: darray[usize] = []
            receiver: usize = ElisaProofKernelCore::add_node(&nodes, "array", "", 0, 0, 0, 0, 3, 0, "", "")
            field: usize = ElisaProofKernelCore::add_node(&nodes, "field", "", receiver, 0, 0, 0, 0, 0, "count", "")
            for length in 0..<9 |nodes, children, facts, receiver, field|:
                nodes[receiver].children_count <- length
                return 10 if not proof_kernel_replay_denial_integer_term(nodes, children, field, facts, 0)
            nodes[receiver].children_count <- 9
            return 11 if proof_kernel_replay_denial_integer_term(nodes, children, field, facts, 0)
            nodes[receiver].children_count <- 3
            nodes[field].name <- "capacity"
            return 12 if proof_kernel_replay_denial_integer_term(nodes, children, field, facts, 0)
            nodes[field].name <- "count"
            for kind in ["ident", "string", "float", "tuple", "construct"] |nodes, children, facts, receiver, field|:
                nodes[receiver].kind <- kind
                return 13 if proof_kernel_replay_denial_integer_term(nodes, children, field, facts, 0)
            nodes[field].left <- nodes.count
            return 14 if proof_kernel_replay_denial_integer_term(nodes, children, field, facts, 0)
            return 15 if proof_kernel_replay_denial_integer_term(nodes, children, field, facts, ElisaProofKernelCore::PROOF_KERNEL_REPLAY_DEPTH_LIMIT)
            0

extend ElisaProof:
    public:
        def audit(report: mutable ProofReport&) -> i64:
            proof_replay_certificates(report)
            return 80 if report.certificates.count != 18
            for certificate in report.certificates:
                return 81 if not certificate.replayed
            ElisaProofKernelReplay::count_controls()

def main() -> i64:
    text: sview = __SOURCE__
    bytes: mutable darray[u8] = []
    for index in 0..<sview_len(text) |bytes|:
        bytes.push(sview_at(text, index))
    bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)
    audit(&report)
'''
harness = harness.replace("__SOURCE__", json.dumps((ROOT / "examples/literal_index.elisa").read_text()))
with tempfile.TemporaryDirectory(prefix="literal-count-denial-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print("literal count denial: 18 certificates replay; bounded lengths accepted; wrong field/receiver, excessive length, missing node and depth refused")
