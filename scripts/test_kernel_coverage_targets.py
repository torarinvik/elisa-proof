"""Keep replay audit coverage targets aligned with production declarations."""

from pathlib import Path
import re
import runpy


if not __debug__:
    raise SystemExit("run without Python -O")

root = Path(__file__).resolve().parents[1]
targets = runpy.run_path(str(root / "test/validate_kernel_replay_standalone.py"))[
    "REQUIRED_VERIFIED_DECLARATIONS"
]
declared = set()
for source in (root / "src/proof/kernel_replay").glob("*.elisa"):
    declared.update(
        re.findall(
            r"^\s*def\s+([A-Za-z_][A-Za-z_0-9]*)\s*\(",
            source.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )

missing = sorted(targets - declared)
if missing:
    raise SystemExit(f"required kernel coverage declarations are missing: {missing}")
if "proof_kernel_replay_term_pin" not in targets:
    raise SystemExit("qualified-constant replay must retain its verified term-pin target")

print(f"kernel coverage targets: all {len(targets)} required declarations exist")
