"""Zero-payload enum values do not provide storage for escaped references."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "examples/plain_enum_resource_call.elisa").read_text()
CASES = (
    ("plain", BASE, True),
    ("early-return", BASE.replace("    state.mode <- mode", "    return if state.mode == mode\n    state.mode <- mode"), True),
    ("payload-reference", BASE.replace("    A\n", "    A(value: i64&)\n"), False),
    ("ambiguous", "module Other:\n    enum Mode:\n        C\n" + BASE, False),
    ("overlapping", BASE.replace("def play(state: mutable State&, mode: Mode)", "def play(state: mutable State&, other: mutable State&, mode: Mode)").replace("    play(state, mode)", "    play(state, state, mode)"), False),
)
for name, source, accepted in CASES:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["summary"]["proven"] == report["summary"]["obligations"]
                assert report["replay"]["gaps"] == 0
            else:
                assert report["summary"]["unproven"] > 0
    print("plain enum resource call:", name, "accepted" if accepted else "refused")
