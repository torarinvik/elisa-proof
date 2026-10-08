"""A call at a validated cast's span must still match its exact source expression."""
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
harness = harness.split("def main()")[0] + r'''
def payload_state(names: mutable darray[sview]&, values: mutable darray[Ast::Expr]&) -> void:
    names.clear()
    values.clear()
    names.extend(["value", "__elisa_rebind_0", "rest", "__elisa_rebind_1"])
    values.extend([Ast::Expr.Absent, Ast::Expr.Ident("value", Ast::pos_at_line(69)), Ast::Expr.Absent, Ast::Expr.Ident("rest", Ast::pos_at_line(69))])

def main() -> i64 can Memory.Allocate, Abort.Panic:
    bytes: mutable darray[u8] = []
    report: mutable ProofReport = proof_empty_report()
    proof_test_parse_and_replay(WIDENING_SOURCE, &bytes, &report)
    report.replay_owner_line <- 67
    report.trace_owner_line <- 75
    casts: mutable darray[Ast::Expr] = []
    proof_replay_deterministic_validated_cast_sites(report, "wide_first", &casts)
    return 140 if casts.count == 0
    body: mutable darray[Ast::Stmt] = []
    owners: mutable usize = 0
    proof_replay_local_binding_find_owner(report.source_declarations, "wide_first", 67, &body, &owners, 0)
    return 141 if owners != 1
    declarations: mutable darray[Ast::Stmt] = []
    raw_call: mutable Ast::Expr = Ast::Expr.Invalid
    cast_initializer: mutable Ast::Expr = Ast::Expr.Invalid
    for statement in body |statement, declarations, raw_call, cast_initializer|:
        match statement:
            Ast::Stmt.Match(_, arms, _):
                for arm in arms |arm, declarations, raw_call, cast_initializer|:
                    for inner in arm.body |inner, declarations, raw_call, cast_initializer|:
                        match inner:
                            Ast::Stmt.VarDecl(name, _, initializer, _):
                                if name == "wide" or name == "later":
                                    declarations.push(inner)
                                    cast_initializer <- initializer if name == "wide"
                                    raw_call <- initializer if name == "later"
                            _:
                                pass
            _:
                pass
    return 142 if declarations.count != 2
    expected: mutable Ast::Expr = Ast::Expr.Invalid
    match raw_call:
        Ast::Expr.Call(callee, _, argument_names, position):
            expected <- Ast::Expr.Call(callee, [Ast::Expr.Ident("__elisa_rebind_1", Ast::pos_at_line(69))], argument_names, position)
        _:
            return 143
    names: mutable darray[sview] = []
    values: mutable darray[Ast::Expr] = []
    payload_state(&names, &values)
    genuine = proof_replay_deterministic_call_source_statements(casts, report.source_declarations, declarations, expected, 74, &names, &values, 0)
    return 144 if not genuine.known or genuine.matches != 1
    # Preserve the entire cast span, but evaluate a different unknown callee there.
    # This must havoc the payload mapping before the subsequent helper call.
    forged: Ast::Expr = Ast::Expr.Call(Ast::Expr.Ident("opaque_write", Ast::expr_pos(cast_initializer)), [], [], Ast::expr_pos(cast_initializer))
    match declarations[0]:
        Ast::Stmt.VarDecl(name, type_expression, _, position):
            declarations[0] <- Ast::Stmt.VarDecl(name, type_expression, forged, position)
        _:
            return 145
    payload_state(&names, &values)
    altered = proof_replay_deterministic_call_source_statements(casts, report.source_declarations, declarations, expected, 74, &names, &values, 0)
    return 146 if altered.known and altered.matches != 0
    return 0
'''
run_source_binding_replay_harness(
    ROOT, ROOT / "examples/loop_invariants_compile.elisa",
    Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")),
    (ROOT / "ELISA_COMPILER_REV").read_text().strip(), harness)
print("Cast state: genuine widening preserves payloads; another call at its exact span resets them")
