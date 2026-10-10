"""Simple branch steps replay without unrelated mutable-binding premises."""
import ast
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
harness = prefix + r'''
def main() -> i64:
    text: sview = "def keep_or_replace(flag: bool, slot: usize, best: usize) -> usize:\n    requires best <= 8\n    requires slot < 8\n    ensure result <= 8\n    b: mutable usize = best\n    if flag:\n        b <- slot\n    b\n"
    bytes: mutable darray[u8] = []
    for index in 0..<sview_len(text) |bytes|:
        bytes.push(sview_at(text, index))
    bytes.push(0)
    file: Ast::File = frontend_parse(&bytes[0])
    report: mutable ProofReport = proof_empty_report()
    proof_check(file, &report)
    report.replay_owner_line <- 1
    report.trace_owner_line <- 8
    widened: mutable bool = false
    reflexive: mutable bool = false
    trace_count: usize = report.traces.records.count
    for index in 0..<trace_count |report, widened, reflexive|:
        trace: ProofFactTrace = report.traces.records[index]
        continue if trace.kind != "branch-join"
        match trace.expression:
            Ast::Expr.Binary(left, operator, right, _):
                if proof_ident_name(left) == "best":
                    return 1 if not proof_replay_fact_trace_entry(&report, index)
                    widened <- true
                if operator == TokenKind.EqEq and proof_ident_name(left) == "b" and proof_ident_name(right) == "b":
                    return 2 if not proof_replay_fact_trace_entry(&report, index)
                    reflexive <- true
            _:
                pass
    return 3 if not widened or not reflexive
    return 0
'''
with tempfile.TemporaryDirectory(prefix="branch-join-premises-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print("branch premises: immutable widening and reflexivity independently replay; complete joined-local regression remains separate")
