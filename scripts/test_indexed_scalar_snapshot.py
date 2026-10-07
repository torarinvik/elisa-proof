"""Indexed scalar equations require an independently checked stable suffix."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
SOURCE = (ROOT / "test/repro/indexed_scalar_snapshot.elisa").read_text()
CALL_SOURCE = (ROOT / "test/repro/indexed_scalar_snapshot_call.elisa").read_text()
GUARDED_SOURCE = (ROOT / "test/repro/indexed_snapshot_guarded_call.elisa").read_text()
CASES = {
    "stable": (SOURCE, True),
    "captured_call_before_snapshot": (CALL_SOURCE, True),
    "captured_call_wrong_bound": (CALL_SOURCE.replace("result < samples.frames[slot]", "result + 1 < samples.frames[slot]"), False),
    "guarded_call_before_snapshot": (GUARDED_SOURCE, True),
    "guarded_call_wrong_bound": (GUARDED_SOURCE.replace("result < samples.frames[slot]", "result + 1 < samples.frames[slot]"), False),
    "wrong_bound": (SOURCE.replace("result < samples.frames[slot]", "result + 1 < samples.frames[slot]"), False),
    "write_after_capture": (SOURCE.replace("samples: Samples&", "samples: mutable Samples&").replace("    held\n", "    samples.frames[slot] <- 0\n    held\n"), False),
    "call_after_capture": (SOURCE.replace("samples: Samples&", "samples: mutable Samples&").replace("    held\n", "    clear(samples, slot)\n    held\n") + "\ndef clear(samples: mutable Samples&, slot: usize) -> void:\n    requires slot < 32\n    samples.frames[slot] <- 0\n", False),
    "branch_write_after_capture": (SOURCE.replace("samples: Samples&", "samples: mutable Samples&").replace("    held\n", "    if value > 0:\n        samples.frames[slot] <- 0\n    held\n"), False),
}
with tempfile.TemporaryDirectory(prefix="elisa-indexed-snapshot-") as directory:
    for name, (source, accepted) in CASES.items():
        path = Path(directory) / (name + ".elisa")
        path.write_text(source)
        for route in ("--json", "--summary-json"):
            result = subprocess.run([BINARY, route, str(path)], capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert report["admission_invariant_failure"] == "", (name, route, report["admission_invariant_failure"])
            assert report["summary"]["semantic_errors"] == 0, (name, route, report["summary"])
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"])
            if accepted:
                assert report["status"] == "proved"
                assert report["summary"]["proven"] == report["summary"]["obligations"] > 0
                assert report["trust"]["kernel_replayed_certificates"] == report["summary"]["obligations"]
                if name == "stable":
                    assert report["summary"]["obligations"] == 5
            else:
                assert report["summary"]["unproven"] > 0, (name, route, report["summary"])
        print("indexed snapshot:", name, "proved" if accepted else "refused")
