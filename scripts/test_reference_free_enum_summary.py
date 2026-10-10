"""Resource summaries audit all enum payloads and nested enum fields."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = """enum Result:
    Good
    Bad
struct Store:
    count: mutable usize
def checked(store: mutable Store&) -> Result:
    store.count <- 1
    Result.Good
def bind(store: mutable Store&) -> void:
    result: Result = checked(store)
"""
CASES = (
    ("plain-enum", BASE, True),
    ("scalar-payload", BASE.replace("    Bad", "    Bad(usize)"), True),
    ("reference-payload", BASE.replace("    Bad", "    Bad(usize&)"), False),
    ("nested-reference-payload", BASE.replace("enum Result:", "struct Payload:\n    reference: usize&\nenum Result:").replace("    Bad", "    Bad(Payload)"), False),
    ("recursive-payload", BASE.replace("    Bad", "    Bad(Result)"), False),
    ("hierarchy", BASE.replace("struct Store:", "enum Child is Result:\n    Ref(usize&)\nstruct Store:"), False),
    ("enum-parameter-field", BASE.replace("struct Store:", "struct Binding:\n    result: Result\nstruct Store:").replace("checked(store: mutable Store&)", "checked(store: mutable Store&, binding: Binding)").replace("bind(store: mutable Store&)", "bind(store: mutable Store&, binding: Binding)").replace("checked(store)", "checked(store, binding)"), True),
)
for name, source, accepted in CASES:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["bind"] if route == "--function-json" else []) + [str(path)]
            run = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(run.stdout)
            assert report["summary"]["semantic_errors"] == 0, (name, route, report)
            assert run.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert report["replay"]["gaps"] == 0, (name, route, report["replay"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"]
            else:
                assert any(item["kind"] == "borrow-call-summary-unsupported" for item in report["findings"]), (name, report["findings"])
    print("reference-free enum summary:", name, "accepted" if accepted else "refused")
