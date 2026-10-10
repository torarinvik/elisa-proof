"""Block assignment checks private scopes and refuses stale outer state."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "examples/captured_search_assignment.elisa").read_text().replace("slot == 4", "slot >= 4")
for name, source, accepted in (
    ("shadowed-search", BASE, True),
    ("distinct-inner", BASE.replace("|slot: usize = 4, store| -> slot:", "|found: usize = 4, store| -> found:"), True),
    ("zero-iterations", BASE.replace("0..<4", "0..<0"), True),
    ("wide-range", BASE.replace("0..<4", "0..<5"), False),
    ("wide-post-guard", BASE.replace("slot >= 4", "slot >= 5"), False),
    ("unbounded-sentinel", BASE.replace("slot >= 4", "slot == 4"), False),
    ("other-outer-write", "struct Store:\n    flags: mutable bool[4]\ndef checked(store: mutable Store&) -> void:\n    index: mutable usize = 0\n    slot: mutable usize = 4\n    slot <- |index|\n        index <- 4\n        0\n    store.flags[index] <- true\n", False),
    ("stale-outer", BASE.replace("-> void:", "-> usize:\n    ensure result == 4").replace("    return if slot >= 4", "    return slot if slot >= 4") + "    slot\n", False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert not report["trust"]["trusted_assumptions"]
            assert report["summary"]["semantic_errors"] == 0
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"] >= 5
                assert report["replay"]["gaps"] == 0
            else:
                assert report["summary"]["unproven"] > 0
    print("value block assignment:", name, "accepted" if accepted else "refused")
