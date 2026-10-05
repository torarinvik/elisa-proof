"""A supported subset must not make an unsupported sibling look fully verified to CLI clients."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-correspondence-partial-"))
source = ROOT / "examples/branch_negation.elisa"
package_result = subprocess.run([str(BINARY), "--package", str(source)], capture_output=True,
                                text=True, timeout=300)
assert package_result.returncode == 0, package_result
package = WORK / "branch-negation.pkg.json"
package.write_text(package_result.stdout)

mixed = WORK / "mixed.elisa"
mixed.write_text("""def nonzero_or_one(x: i64) -> i64:
    ensure result != 0
    if x == 0:
        return 1
    else:
        return x

def half(x: i64) -> i64:
    ensure result >= 0
    return x / 2
""")
result = subprocess.run([str(BINARY), "--correspondence", str(package), str(mixed)],
                        capture_output=True, text=True, timeout=300)
assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
report = json.loads(result.stdout)
assert report["source_admissible"] is True and report["package"]["status"] == "replayed", report
assert {item["name"]: item["status"] for item in report["functions"]} == {
    "nonzero_or_one": "checked", "half": "unsupported",
}, report
assert report["summary"] == {
    "checked": 1, "unmatched": 0, "unsupported": 1,
    "coverage": "partial", "exit_code": 1,
}, report

print("correspondence partial coverage: report is explicit and exits nonzero")
