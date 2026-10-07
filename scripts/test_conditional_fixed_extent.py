"""Fixed extents survive conditional record updates without stale field bounds."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "test/repro/conditional_record_write_fixed_extent.elisa").read_text()
for name, source, accepted in (
    ("conditional-fixed-extent", BASE, True),
    ("conditional-expression", BASE.replace("first: bool = store.flags[index]", "first: bool = store.flags[index] if index == 0 else false"), True),
    ("call-argument", ("def identity(value: bool) -> bool:\n    return value\n" + BASE).replace("first: bool = store.flags[index]", "first: bool = identity(store.flags[index])"), True),
    ("slice", BASE.replace("first: bool = store.flags[index]", "first: view[bool] = store.flags[0:4]"), True),
    ("bad-slice", BASE.replace("first: bool = store.flags[index]", "first: view[bool] = store.flags[0:5]"), False),
    ("shadowed-array", ("struct Small:\n    flags: mutable bool[1]\n" + BASE).replace("        first: bool = store.flags[index]", "        region shadow_scope:\n            store: Small = Small{flags: [false]}\n            first: bool = store.flags[1]"), False),
    ("dynamic-array", BASE.replace("bool[4]", "darray[bool]"), False),
    ("out-of-bounds", BASE.replace("0..<4", "0..<5").replace("        break if index >= store.count\n", ""), False),
    ("changed-field", BASE.replace("        first: bool = store.flags[index]", "        first: bool = store.flags[store.count]").replace("            store.active <- true", "            store.count <- 4"), False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            run = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(run.stdout)
            assert report["summary"]["semantic_errors"] == 0, (name, route, report)
            assert run.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert report["replay"]["gaps"] == 0, (name, route, report["replay"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"]
            else:
                assert report["findings"]
    print("conditional fixed extent:", name, "accepted" if accepted else "refused")
