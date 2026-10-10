"""Compile source-boundary checks for indexed-copy equality and forged trace/source controls."""
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
source = (ROOT / 'examples/collection_frames.elisa').read_text()
scalar_module = ast.parse((ROOT / "scripts/test_scalar_copy_bound_source.py").read_text())
scalar_harness = next(ast.literal_eval(node.value.right) for node in scalar_module.body
                      if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "harness" for t in node.targets)
                      and isinstance(node.value, ast.BinOp))
constructor = scalar_harness.split("        def source_gate", 1)[0]
harness = prefix + constructor + r'''
        def source_gate(report: mutable ProofReport&, trace: ProofFactTrace) -> bool:
            report.replay_owner_line <- 9
            report.trace_owner_line <- 15
            proof_replay_index_copy_equality_source(report, trace)

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
    trace_count: usize = report.traces.records.count
    for index in 0..<trace_count |report|:
        candidate: ProofFactTrace = report.traces.records[index]
        continue if candidate.kind != "proof-step" or candidate.line != 12 or candidate.name != "swap_second"
        match candidate.expression:
            Ast::Expr.Binary(left, TokenKind.EqEq, right, position):
                continue if proof_ident_name(left) != "t" or proof_ident_name(right) != "a"
                return 1 if not source_gate(&report, candidate)
                return 2 if source_gate(&report, forged_trace(candidate, candidate.expression, 13, candidate.kind, 0))
                return 3 if source_gate(&report, forged_trace(candidate, Ast::Expr.Binary(Ast::Expr.Ident("evil", position), TokenKind.EqEq, right, position), 12, candidate.kind, 0))
                return 4 if source_gate(&report, forged_trace(candidate, Ast::Expr.Binary(left, TokenKind.EqEq, Ast::Expr.Ident("b", position), position), 12, candidate.kind, 0))
                return 5 if source_gate(&report, forged_trace(candidate, candidate.expression, 12, "local-binding", 0))
                return 6 if source_gate(&report, forged_trace(candidate, candidate.expression, 12, candidate.kind, 1))
                __CONTROLS__
                return 0
            _:
                pass
    return 99
'''
controls = {
    "wrong_index": source.replace("    t: i64 = xs[i]", "    t: i64 = xs[j]"),
    "wrong_value": source.replace("xs[i] == a", "xs[i] == b"),
    "mutable_copy": source.replace("t: i64 =", "t: mutable i64 ="),
    "rebound_copy": source.replace("    xs[i] <- xs[j]", "    t <- b"),
    "pre_copy_write": source.replace("    ensure result == a", "    xs[i] <- b"),
    "mutable_value": source.replace("a: i64", "a: mutable i64"),
    "mutable_index": source.replace("i: usize", "i: mutable usize"),
    "shadowed_primitive": source + "\ntype i64 = u64\n",
    "missing_equality": source.replace("and xs[i] == a", "and i < j"),
    "nonconjunctive_equality": source.replace("and xs[i] == a", "or xs[i] == a"),
}
lines = []
for number, (name, changed) in enumerate(controls.items(), 10):
    lines += ["other_bytes: mutable darray[u8] = []", "other_report: mutable ProofReport = proof_empty_report()"] if number == 10 else []
    lines += [f"parse_source({json.dumps(changed)}, &other_bytes, &other_report)", f"return {number} if source_gate(&other_report, candidate)"]
harness = harness.replace("__SOURCE__", json.dumps(source)).replace("__CONTROLS__", "\n                ".join(lines))
with tempfile.TemporaryDirectory(prefix="index-copy-equality-source-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print("indexed-copy equality: authentic scalar consequence accepted; fifteen forged trace/source controls refused")
