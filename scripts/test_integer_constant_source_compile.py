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
extend ElisaProof:
    public:
        def audit(report: mutable ProofReport&, changed: darray[Ast::File]&) -> i64:
            proof_replay_certificates(report)
            return 80 if report.certificates.count != 23
            return 99 if not proof_name_is_reserved_internal("__elisa_primitive_integer_type")
            for certificate in report.certificates:
                return 81 if not certificate.replayed
            positives: darray[sview] = ["else_path_le", "scalar_store", "subtraction_path_bound", "subtraction_path_bound_u64"]
            for index in 0..<positives.count |report, positives|:
                found: mutable bool = false
                for summary in report.declaration_details |positives, index, found|:
                    if summary.name == positives[index]:
                        found <- true
                        return 50 + index.i64() if not summary.verified
                return 60 + index.i64() if not found
            for summary in report.declaration_details:
                if summary.name == "else_path_negative_control" or summary.name == "subtraction_path_strict_negative" or summary.name == "floating_nan_negative_control":
                    return 70 if summary.verified
            report.replay_owner_line <- 37
            for trace in report.traces.records |report, changed|:
                continue if trace.name != "subtraction_path_bound_u64" or not proof_marker_has_callee(trace.expression, "__elisa_primitive_integer_type")
                return 90 if not proof_replay_integer_constant_source_valid(report, trace)
                original: darray[Ast::Decl] = report.source_declarations
                for index in 0..<changed.count |report, trace, changed|:
                    combined: mutable darray[Ast::Decl] = []
                    if index == 4:
                        combined.extend(original)
                        combined.extend(changed[index].top_decls)
                    report.source_declarations <- combined if index == 4 else changed[index].top_decls
                    return 91 + index.i64() if proof_replay_integer_constant_source_valid(report, trace)
                report.source_declarations <- original
                position: Ast::Pos = Ast::expr_pos(trace.expression)
                callee: Ast::Expr = Ast::Expr.Ident("__elisa_primitive_integer_type", position)
                term: Ast::Expr = Ast::Expr.Ident("U64_MAX", position)
                expressions: darray[Ast::Expr] = [Ast::Expr.Call(callee, [], [], position), Ast::Expr.Call(callee, [term, term], [], position), Ast::Expr.Call(callee, [term], ["named"], position), Ast::Expr.Call(Ast::Expr.Paren(callee, position), [term], [], position)]
                for expression in expressions |report, trace|:
                    forged: ProofFactTrace = ProofFactTrace{expression: expression, kernel_expression: trace.kernel_expression, kind: trace.kind, line: trace.line, name: trace.name, dependency: trace.dependency, premises_start: trace.premises_start, premises_count: trace.premises_count, kernel_premises_start: trace.kernel_premises_start, kernel_premises_count: trace.kernel_premises_count, summary_bindings_start: trace.summary_bindings_start, summary_bindings_count: trace.summary_bindings_count, summary_requires_start: trace.summary_requires_start, summary_requires_count: trace.summary_requires_count, summary_ensure_index: trace.summary_ensure_index, owner_line: trace.owner_line}
                    return 98 if proof_replay_integer_constant_source_valid(report, forged)
                report.replay_owner_line <- 38
                return 96 if proof_replay_integer_constant_source_valid(report, trace)
                return 0
            97

def main() -> i64:
    texts: darray[sview] = __SOURCES__
    buffers: mutable darray[darray[u8]] = []
    files: mutable darray[Ast::File] = []
    for text in texts |buffers, files|:
        bytes: mutable darray[u8] = []
        for index in 0..<sview_len(text) |bytes|:
            bytes.push(sview_at(text, index))
        bytes.push(0)
        file: Ast::File = frontend_parse(&bytes[0])
        buffers.push(bytes)
        files.push(file)
    report: mutable ProofReport = proof_empty_report()
    proof_check(files[0], &report)
    changed: mutable darray[Ast::File] = []
    for index in 1..<files.count |changed|:
        changed.push(files[index])
    audit(&report, changed)
'''

source = (ROOT / "examples/return_branch_path_fact.elisa").read_text()
sources = [source,
           source.replace("const U64_MAX: u64 = 18446744073709551615", "const U64_MAX: f64 = 1.0"),
           source.replace("subtraction_path_bound_u64(now: u64, delay: u64)", "subtraction_path_bound_u64(now: u64, U64_MAX: f64)"),
           source.replace("def subtraction_path_bound_u64(now: u64, delay: u64) -> u8:", "def subtraction_path_bound_u64(now: u64, delay: u64) -> u8:\n            U64_MAX: f64 = 1.0"),
           source.replace("const U64_MAX: u64 = 18446744073709551615", "const U64_MAX: u64 = 5"),
           "\n" * 36 + "def subtraction_path_bound_u64(now: u64, delay: u64) -> u8:\n    return 0\n",
           source + "\ntype u64 = f64\n",
           source.replace("const U64_MAX: u64 = 18446744073709551615", "global mutable U64_MAX: mutable u64 = 18446744073709551615")]
harness = harness.replace("__SOURCES__", "[" + ",".join(json.dumps(s) for s in sources) + "]")
with tempfile.TemporaryDirectory(prefix="integer-constant-source-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run([str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)], cwd=COMPILER, check=True)
    subprocess.run([str(binary)], check=True, timeout=60)
print("integer constant: positive contracts/certificates preserved; float/parameter/local/initializer/owner substitutions refused")
