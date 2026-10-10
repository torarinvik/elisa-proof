"""Authenticate captured pop facts from source; changed claims fail closed."""
from pathlib import Path
import os
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
COMPILER_ROOT = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler"))
STAGE1 = COMPILER_ROOT / "bin" / "elisac-stage1"
STAGE1_WRAPPER = COMPILER_ROOT / "scripts" / "elisac_stage1.sh"
FRESHNESS_CHECK = COMPILER_ROOT / "scripts" / "assert_stage1_fresh.sh"


HARNESS = r'''include "../../Elisa-compiler/elisacore_std/elisacore_runtime_prelude.elisa"
include "../../Elisa-compiler/elisacore_std/collections.elisa"
include "../../Elisa-compiler/elisacore_std/elisacore_runtime_strings.elisa"
include "../../Elisa-compiler/src/semantic/semantic.elisa"
include "../src/proof/kernel_core.elisa"
include "../src/proof/operator_impl_model.elisa"
include "../src/proof/model/enum_index.elisa"
include "../src/proof/model/findings.elisa"
include "../src/proof/model.elisa"
include "../src/proof/model/lemma_table.elisa"
include "../src/proof/model/report_invariants.elisa"
include "../src/proof/kernel.elisa"
include "../src/proof/kernel_intern.elisa"
include "../src/proof/expr.elisa"
include "../src/proof/linear.elisa"
include "../src/proof/resources.elisa"
include "../src/proof/check.elisa"
include "../src/proof/kernel_replay.elisa"
include "../src/proof/replay.elisa"
include "../src/proof/tactics.elisa"

using Ast
using ElisaProof
def test_source(text: sview, local: sview, value: i64, shift: i64) -> bool can[Memory.Allocate, Abort.Panic]:
    source: mutable darray[u8] = []
    for i in 0..<sview_len(text) |source|:
        source.push(sview_at(text, i))
    source.push(0)
    file: Ast::File = frontend_parse(&source[0])
    context = ElisaProofFrameSource::owner(&file.top_decls, "take", 1)
    return false if not context.known
    position: mutable Ast::Pos = Ast::pos_at_line(0)
    for statement in context.body |position|:
        match statement:
            Ast::Stmt.VarDecl("x", _, _, found):
                position <- found
            _:
                pass
    position.column <- position.column + 1 if shift == 1
    position.end_column <- position.end_column + 1 if shift == 2
    expression: Ast::Expr = Ast::Expr.Binary(Ast::Expr.Ident(local, position), TokenKind.EqEq, Ast::Expr.IntLit(value, position), position)
    return ElisaProofFrameSource::pop_value_source(&file.top_decls, "take", 1, position.line, expression)

def main() -> i64 can[Memory.Allocate, Abort.Panic]:
    return 1 if not test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 1 and v[v.count - 1] == 9\n    ensure result == 9\n    x: u32 = v.pop()\n    return x\n", "x", 9, 0)
    return 2 if test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 1 and v[v.count - 1] == 9\n    ensure result == 9\n    x: u32 = v.pop()\n    return x\n", "x", 8, 0)
    return 3 if test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 1 and v[v.count - 1] == 9\n    ensure result == 9\n    x: u32 = v.pop()\n    return x\n", "wrong", 9, 0)
    return 4 if test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 1 and v[v.count - 1] == 9\n    ensure result == 9\n    x: u32 = v.pop()\n    return x\n", "x", 9, 1)
    return 5 if test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 1 and v[0] == 9\n    ensure result == 9\n    x: u32 = v.pop()\n    return x\n", "x", 9, 0)
    return 6 if test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 1 and v[v.count - 1] == 9\n    ensure result == 9\n    x: u32 = v.pop()\n    x <- 8\n    return x\n", "x", 9, 0)
    return 7 if test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 1 and v[v.count - 1] == 9\n    ensure result == 9\n    v.pop()\n    x: u32 = v.pop()\n    return x\n", "x", 9, 0)
    return 8 if not test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 1 and v[v.count - 1] == 9\n    ensure result == 9\n    x: u32 = v.pop()\n    v.pop()\n    return x\n", "x", 9, 0)
    return 9 if test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 1 and v[v.count - 1] == 9\n    ensure result == 9\n    x: u32 = v.pop()\n    return x\n", "x", 9, 2)
    return 10 if test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 1 and v[v.count - 1] == 9\n    ensure result == 9\n    x: u32 = v.pop()\n    return x\n\ndef pop(v: mutable darray[u32]&) -> u32:\n    return 7\n", "x", 9, 0)
    return 11 if test_source("def take(v: darray[u32]) -> u32:\n    requires v.count >= 1 and v[v.count - 1] == 9\n    ensure result == 9\n    x: u32 = v.pop()\n    return x\n", "x", 9, 0)
    return 12 if test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 0 and v[v.count - 1] == 9\n    ensure result == 9\n    x: u32 = v.pop()\n    return x\n", "x", 9, 0)
    return 13 if test_source("def take(v: mutable darray[u32]&) -> u32:\n    requires v.count >= 1 and v[v.count - 1] == 9\n    ensure result == 9\n    x: u64 = v.pop()\n    return x\n", "x", 9, 0)
    return 0
'''

def main() -> None:
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    subprocess.run(["bash", str(FRESHNESS_CHECK), str(STAGE1)], check=True, cwd=COMPILER_ROOT)

    with tempfile.TemporaryDirectory(prefix="pop-snapshot-source-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source = directory / "pop_snapshot_source.elisa"
        executable = directory / "pop_snapshot_source"
        compiler_include = str(COMPILER_ROOT.resolve()) + "/"
        harness = HARNESS.replace("../../Elisa-compiler/", compiler_include).replace(
            'include "../src/', 'include "../../src/'
        )
        source.write_text(harness, encoding="utf-8")
        compiled = subprocess.run(
            [str(STAGE1_WRAPPER), "-emit", "exe", "-O2", "-o", str(executable), str(source)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=300,
        )
        if compiled.returncode:
            raise AssertionError(f"fresh Stage1 harness compile failed:\n{compiled.stdout}\n{compiled.stderr}")
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)

    print("pop source snapshots: honest and later-pop captures accepted; wrong literal/local/span, first-slot, local write and prior pop refused")


if __name__ == "__main__":
    main()
