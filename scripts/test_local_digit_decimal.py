"""Local digit loop bindings replay only their exact bounded source shape."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
BASE = (ROOT / "examples/local_digit_decimal_loop.elisa").read_text()
CASES = (
    ("local-digit", BASE, True),
    ("error-guard-prefix", BASE.replace("struct Source:", "error ParseError:\n    Empty\nstruct Source:").replace("-> u64:", "-> u64 error[ParseError]:").replace("    value: u64 =", "    raise ParseError.Empty if stop == 0\n    value: u64 ="), True),
    ("field-precondition", BASE.replace("    bytes: u8[8]", "    bytes: u8[8]\n    length: usize").replace("requires stop <= 8", "requires stop <= source.length and source.length <= 8"), True),
    ("small-cap", BASE.replace("1000000000000000000", "1000000"), True),
    ("wide-digit", BASE.replace("byte <= 57", "byte <= 58"), False),
    ("wrong-offset", BASE.replace("byte - 48", "byte - 47"), False),
    ("wide-fallback", BASE.replace("else 0", "else 10"), False),
    ("wrong-threshold", BASE.replace("CAP / 10", "CAP / 9"), False),
    ("wrong-multiplier", BASE.replace("value * 10", "value * 11"), False),
    ("earlier-rebind", BASE.replace("    value: u64 =", "    other: mutable u64 = 0\n    other <- other + 1\n    value: u64 ="), False),
    ("mutated-digit", BASE.replace("digit: u64 =", "digit: mutable u64 =").replace("            value <- CAP", "            digit <- 42\n            value <- CAP"), False),
)
for name, source, accepted in CASES:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["checked"] if route == "--function-json" else []) + [str(path)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == (0 if accepted else 1), (name, route, report["summary"], report["replay"])
            assert not report["trust"]["trusted_assumptions"]
            if accepted:
                assert report["replay"]["gaps"] == 0
                assert report["summary"]["proven"] == report["summary"]["obligations"]
            else:
                assert report["summary"]["unproven"] > 0
    print("local digit decimal:", name, "accepted" if accepted else "refused")
