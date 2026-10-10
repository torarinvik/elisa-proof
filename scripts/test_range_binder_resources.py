"""Range binders shadow values; genuine borrow contracts remain refused."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))


def run(name):
    result = subprocess.run([BINARY, "--json", str(ROOT / "examples" / name)],
                            capture_output=True, text=True, timeout=60)
    return result.returncode, json.loads(result.stdout)


code, report = run("source_context_scope.elisa")
assert code == 0 and report["status"] == "proved", report["findings"]
assert report["summary"]["semantic_errors"] == 0
assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0
assert report["replay"]["gaps"] == 0
code, report = run("rejected_for_shadow.elisa")
assert code == 1 and report["summary"]["unproven"] > 0
code, report = run("contract_old_resource_rejected.elisa")
assert code == 1
assert any(finding["name"] == "contract_old_address"
           and finding["kind"] == "borrow-contract-unsupported"
           for finding in report["findings"]), report["findings"]
print("range binder scope restored; false shadow claim and genuine borrow contract refused")
