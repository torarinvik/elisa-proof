"""Loops carrying `invariant` and `decreases` clauses compile, link and run under the pinned
compiler, and prove (BACKLOG E-03). Each invariant is then mutated, by negation and by tightening
a non-strict comparison, and every mutant must leave the proof incomplete: an invariant the
checker accepted without reading would survive a mutation."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
COMPILER = os.environ.get("ELISA_COMPILER_BIN", "")
FIXTURE = ROOT / "examples/loop_invariants_compile.elisa"


def prove(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=120)
    return result.returncode, json.loads(result.stdout)


status, data = prove(FIXTURE)
assert status == 0 and data["status"] == "proved" and data["findings"] == [], data["findings"]
assert data["replay"]["gaps"] == 0, data["replay"]

source = FIXTURE.read_text()
lines = source.split("\n")
invariant_lines = [index for index, line in enumerate(lines) if line.strip().startswith("invariant ")]
assert len(invariant_lines) == 4, invariant_lines
with tempfile.TemporaryDirectory() as scratch:
    mutants = 0
    for index in invariant_lines:
        indent, claim = lines[index].split("invariant ", 1)
        variants = [f"not ({claim})"]
        if ">=" in claim:
            variants.append(claim.replace(">=", ">", 1))
        if "<=" in claim:
            variants.append(claim.replace("<=", "<", 1))
        for variant in variants:
            mutated = list(lines)
            mutated[index] = f"{indent}invariant {variant}"
            path = Path(scratch) / f"mutant_{mutants}.elisa"
            path.write_text("\n".join(mutated))
            status, data = prove(path)
            assert status != 0 and data["status"] != "proved", (index + 1, variant, data["status"])
            mutants += 1
    assert mutants == 8, mutants

    if not COMPILER:
        sys.exit("loop invariants compile: ELISA_COMPILER_BIN is not set")
    obj = Path(scratch) / "loops.o"
    exe = Path(scratch) / "loops"
    built = subprocess.run([COMPILER, "-permissive", "-emit", "obj", "-O0", "-o", str(obj), str(FIXTURE)], capture_output=True, text=True, timeout=600)
    assert built.returncode == 0 and obj.exists(), built.stderr
    symbols = subprocess.run(["nm", str(obj)], capture_output=True, text=True).stdout
    for name in ("bounded_counter", "countdown", "count_up", "stop_early"):
        assert re.search(rf"\b_?{name}\b", symbols), f"{name} was not emitted"
    linked = subprocess.run(["cc", "-o", str(exe), str(obj)], capture_output=True, text=True)
    assert linked.returncode == 0, linked.stderr
    ran = subprocess.run([str(exe)], timeout=60)
    assert ran.returncode == 0, ran.returncode

print("loop invariants compile: invariant loops build and run, and every invariant mutant is refused")
