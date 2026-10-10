"""Finite searches preserve caller guards; effectful or unsupported bodies do not."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "test/repro/read_only_search_call_guard.elisa").read_text()
MUTABLE = BASE.replace("search(store: Store&)", "search(store: mutable Store&)").replace("    for index", "    store.count <- 4\n    for index")
GLOBAL = BASE.replace("def search", "global mutable active: bool = false\n\ndef search").replace("if store.flags[index]", "if store.flags[index] or active")
CALLBACK = BASE.replace("def search", "global mutable ticks: usize = 0\n\ndef flag() -> bool:\n    ticks <- ticks + 1\n    false\n\ndef search").replace("if store.flags[index]", "if flag()")
for name, source, accepted, gaps in (
    ("read-only", BASE, True, 0),
    ("zero-iterations", BASE.replace("0..<4", "0..<0"), True, 0),
    ("mutable-callee", MUTABLE, False, 0),
    ("mutable-global-read", GLOBAL, False, 0),
    # Existing preservation replay limitation remains visible on effectful calls.
    ("effectful-callback", CALLBACK, False, 1),
    ("insufficient-guard", BASE.replace("store.count >= 4", "store.count > 4"), False, 0),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            run = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(run.stdout)
            assert report["summary"]["semantic_errors"] == 0, (name, route, report["summary"])
            assert run.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert report["replay"]["gaps"] == gaps, (name, route, report["replay"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"]
            else:
                assert report["findings"]
    print("pure search:", name, "accepted" if accepted else "refused")
