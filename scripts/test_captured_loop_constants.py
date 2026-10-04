"""Constant discovery in captured loops must preserve scope and refuse false invariants."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def check(source, proved):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "captured.elisa"
        path.write_text(source)
        run = subprocess.run([str(BINARY), "--json", str(path)],
                             capture_output=True, text=True, timeout=60)
    data = json.loads(run.stdout)
    assert run.returncode == (0 if proved else 1), (run.returncode, data.get("findings"), run.stderr)
    assert (data["status"] == "proved") == proved, data
    assert data["replay"]["gaps"] == 0, data["replay"]
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]
    return data


template = """module M:
    const N: usize = 9
    def f({parameter}) -> usize:
        count: mutable usize = {initial}
        for i in 0..<N |count|:
            invariant count <= N
            count <- count
        count
"""
check(template.format(parameter="", initial=0), True)
check("""module M:
    const N: usize = 9
    def f() -> usize:
        for i in 0..<N |count: usize = 0| -> count:
            invariant count <= N
            count <- count
""", True)
check("""module M:
    const N: usize = 9
    def f() -> usize:
        result: usize =
            for i in 0..<N |count: usize = 0| -> count:
                invariant count <= N
                count <- count
        result
""", True)
check(template.format(parameter="", initial=10), False)
# A parameter shadows the module constant: N may be zero, so count=1 is not safe.
check(template.format(parameter="N: usize", initial=1), False)
# Constants in a sibling namespace must not be imported as the local one.
check("module Other:\n    const N: usize = 99\n" +
      template.replace("const N: usize = 9", "const N: usize = 0").format(parameter="", initial=1), False)
check(template.replace("|count|", "|count, count|").format(parameter="", initial=0), False)
deep = "module M:\n    const N: usize = 9\n    def f() -> usize:\n        count: mutable usize = 0\n"
for depth in range(70):
    deep += " " * (8 + depth * 4) + "if true:\n"
indent = " " * (8 + 70 * 4)
deep += indent + "for i in 0..<N |count|:\n" + indent + "    invariant count <= N\n" + indent + "    count <- count\n        count\n"
budget = check(deep, False)
assert any("budget" in finding["kind"] for finding in budget["findings"]), budget["findings"]
print("captured loop constants: exact module value imported; false and shadowed invariants refused")
