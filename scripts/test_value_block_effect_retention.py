"""Pure conditional loop values retain guards; nested mutations revoke them."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
# Entry replay of a scalar invariant in a nested assignment is a separate gap.
# A true invariant isolates effect classification and post-search guard retention.
BASE = (ROOT / "test/repro/conditional_search_field_bound.elisa").read_text().replace("invariant hit <= 4", "invariant true")
NESTED = BASE.replace("            break index", "            scratch: usize = |store|\n                store.count <- 4\n                0\n            break index")
CALL = BASE.replace("def checked(", "def mutate(store: mutable Store&) -> bool:\n    store.count <- 4\n    false\n\ndef checked(").replace("            break index", "            scratch: bool = mutate(store)\n            break index")
for name, source, accepted in (
    ("conditional-read", BASE, True),
    ("zero-iterations", BASE.replace("0..<4", "0..<0"), True),
    ("nested-record-write", NESTED, False),
    ("mutating-call", CALL, False),
    ("direct-record-write", BASE.replace("            break index", "            store.count <- 4\n            break index"), False),
    ("wrong-entry", BASE.replace("store.count >= 4", "store.count > 4"), False),
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
    print("block effects:", name, "accepted" if accepted else "refused")
