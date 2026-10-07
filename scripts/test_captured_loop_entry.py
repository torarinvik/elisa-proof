"""Header initializer facts belong only to the original invariant entry."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
SOURCE = (ROOT / "test/repro/captured_loop_sentinel.elisa").read_text()
CASES = {
    "valid": (SOURCE, True),
    "invalid_initializer": (SOURCE.replace("best: usize = 32", "best: usize = 33"), False),
    "invalid_preservation": (SOURCE.replace("best <- slot if", "best <- slot + 33 if"), False),
    "stale_equality_after_loop": (SOURCE.replace("ensure result <= 32", "ensure result == 32"), False),
    "stale_lower_bound_after_loop": (SOURCE.replace("ensure result <= 32", "ensure result >= 32"), False),
    "wrong_entry_bound": (SOURCE.replace("invariant best <= 32", "invariant best <= 31"), False),
    "conditional_invalid_preservation": (SOURCE.replace("best <- slot if slot == pick", "if slot == pick:\n            best <- 64"), False),
}
with tempfile.TemporaryDirectory(prefix="elisa-captured-entry-") as directory:
    for name, (source, accepted) in CASES.items():
        path = Path(directory) / (name + ".elisa")
        path.write_text(source)
        for route in ("--json", "--summary-json"):
            result = subprocess.run([BINARY, route, str(path)], capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert report["admission_invariant_failure"] == "", (name, route)
            assert report["summary"]["semantic_errors"] == 0, (name, route)
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"])
            if accepted:
                assert report["status"] == "proved"
                assert report["summary"]["proven"] == report["summary"]["obligations"] == 4
                assert report["trust"]["kernel_replayed_certificates"] == 4
            else:
                assert report["summary"]["unproven"] > 0, (name, route)
        print("captured loop entry:", name, "proved" if accepted else "refused")
