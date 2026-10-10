"""Original high-bit u64 exclusion fixture must replay without accepting false boundaries."""
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
harness = prefix + r'''extend ElisaProofKernelReplay:
    public:
        def unsigned_leaf_width_gate() -> i64:
            nodes: mutable darray[ElisaProofKernelCore::ProofKernelNode] = []
            raw: usize = ElisaProofKernelCore::add_node(&nodes, "int", "", 0, 0, 0, 0, 0, -1, "", "")
            return 40 if not proof_kernel_replay_constant_fits_unsigned(nodes, raw, 64)
            for width in [8, 16, 32] |nodes, raw|:
                return 41 if proof_kernel_replay_constant_fits_unsigned(nodes, raw, width)
            one: usize = ElisaProofKernelCore::add_node(&nodes, "int", "", 0, 0, 0, 0, 0, 1, "", "")
            negated: usize = ElisaProofKernelCore::add_node(&nodes, "unary", "-", one, 0, 0, 0, 0, 0, "", "")
            return 42 if proof_kernel_replay_constant_fits_unsigned(nodes, negated, 64)
            difference: usize = ElisaProofKernelCore::add_node(&nodes, "binary", "-", one, raw, 0, 0, 0, 0, "", "")
            return 43 if proof_kernel_replay_constant_fits_unsigned(nodes, difference, 64)
            return 44 if proof_kernel_replay_constant_fits_unsigned(nodes, nodes.count, 64)
            0

extend ElisaProof:
    public:
        def width_replay_gate(text: sview, expected: usize, positive: bool) -> i64:
            bytes: mutable darray[u8] = []
            for index in 0..<sview_len(text) |bytes|:
                bytes.push(sview_at(text, index))
            bytes.push(0)
            file: Ast::File = frontend_parse(&bytes[0])
            report: mutable ProofReport = proof_empty_report()
            proof_check(file, &report)
            proof_replay_certificates(&report)
            return 1 if report.replay_gaps != 0 or report.certificates.count != expected
            return 2 if positive and report.findings.count != 0
            return 3 if not positive and report.findings.count == 0
            0

def main() -> i64:
    direct: i64 = ElisaProofKernelReplay::unsigned_leaf_width_gate()
    return direct if direct != 0
    __CONTROLS__
    0
'''
fixtures = [('strict_order_disequality', 12, True),
            ('rejected_u64_max_same_value_disequality', 1, False),
            ('rejected_u64_unary_negative_same_value', 1, False)]
controls = []
for index, (name, count, positive) in enumerate(fixtures):
    controls.append('result_%d: i64 = width_replay_gate(%s, %d, %s)' %
                    (index, json.dumps((ROOT / ('examples/' + name + '.elisa')).read_text()), count, str(positive).lower()))
    controls.append('return result_%d + %d if result_%d != 0' % (index, index * 10, index))
harness = harness.replace('__CONTROLS__', '\n    '.join(controls))
with tempfile.TemporaryDirectory(prefix='unsigned-literal-width-replay-') as temporary:
    path = Path(temporary) / 'main.elisa'
    binary = Path(temporary) / 'gate'
    path.write_text(harness)
    subprocess.run([str(COMPILER / 'scripts/elisac_stage1.sh'), str(path), '-emit', 'exe', '-O0', '-o', str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print('unsigned literal width: original 12 certificates replay; same-value and unary-negative controls refused')
