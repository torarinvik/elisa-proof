"""Compile typed loop-binder integer ordering and kernel refusal controls."""
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
source = (ROOT / "examples/guard_and_flag_facts.elisa").read_text()
harness = prefix + r'''
extend ElisaProofKernelReplay:
    public:
        def integer_atom(nodes: darray[ElisaProofKernelCore::ProofKernelNode]&, children: darray[usize]&, facts: darray[usize], root: usize) -> bool:
            proof_kernel_replay_denial_integer_term(nodes, children, root, facts, 0)
        def width_fact(nodes: darray[ElisaProofKernelCore::ProofKernelNode]&, children: darray[usize]&, fact: usize, root: usize) -> bool:
            single: darray[usize] = [fact]
            proof_kernel_replay_place_marker_width(nodes, children, single, root) != 0

extend ElisaProof:
    public:
        def audit(report: mutable ProofReport&) -> i64:
            proof_replay_certificates(report)
            return 1 if report.certificates.count != 9
            for certificate in report.certificates |report|:
                return 2 if not certificate.replayed
            for certificate in report.certificates |report|:
                continue if certificate.name != "k3" or certificate.line != 12 or certificate.rule != "index-upper"
                root: usize = report.kernel.nodes[certificate.kernel_goal].left
                facts: mutable darray[usize] = []
                without_width: mutable darray[usize] = []
                marked: mutable usize = 0
                for index in 0..<certificate.kernel_facts_count |report, certificate, root, facts, without_width, marked|:
                    fact: usize = report.kernel.certificate_facts[certificate.kernel_facts_start + index]
                    facts.push(fact)
                    if ElisaProofKernelReplay::width_fact(report.kernel.nodes, report.kernel.children, fact, root):
                        marked <- marked + 1
                    else:
                        without_width.push(fact)
                return 3 if marked != 1
                return 4 if not ElisaProofKernelReplay::integer_atom(report.kernel.nodes, report.kernel.children, facts, root)
                return 5 if ElisaProofKernelReplay::integer_atom(report.kernel.nodes, report.kernel.children, without_width, root)
                return 6 if ElisaProofKernelReplay::proof_kernel_replay_goal_report(&report.kernel.nodes, &report.kernel.children, without_width, certificate.kernel_goal)
                original: ElisaProofKernelCore::ProofKernelNode = report.kernel.nodes[root]
                malformed: mutable ElisaProofKernelCore::ProofKernelNode = original
                malformed.children_count <- 1
                report.kernel.nodes[root] <- malformed
                return 7 if ElisaProofKernelReplay::integer_atom(report.kernel.nodes, report.kernel.children, facts, root)
                report.kernel.nodes[root] <- original
                tag: usize = report.kernel.children[original.children_start + 1]
                old_tag: ElisaProofKernelCore::ProofKernelNode = report.kernel.nodes[tag]
                float_tag: mutable ElisaProofKernelCore::ProofKernelNode = old_tag
                float_tag.kind <- "float"
                report.kernel.nodes[tag] <- float_tag
                return 8 if ElisaProofKernelReplay::integer_atom(report.kernel.nodes, report.kernel.children, facts, root)
                report.kernel.nodes[tag] <- old_tag
                return 9 if not ElisaProofKernelReplay::integer_atom(report.kernel.nodes, report.kernel.children, facts, root)
                return 0
            99

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
harness = harness.replace("__SOURCE__", json.dumps(source))
with tempfile.TemporaryDirectory(prefix="loop-integer-width-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print("loop integer width: 9 certificates replayed; missing width, malformed tuple and floating tag refused")
