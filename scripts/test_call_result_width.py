"""A returned call-bound local keeps its call's summary, a closed constant beside a call result
is read at the callee's declared signed width, and a call result nested in another call's
arguments generalizes with it; nothing else is."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def check(name):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / name)],
                         capture_output=True, text=True, timeout=60)
    data = json.loads(run.stdout)
    assert data["summary"]["semantic_errors"] == 0, data
    assert data["replay"]["gaps"] == 0, data["replay"]
    assert data["replay"]["certificates"] == data["replay"]["replayed"], data["replay"]
    return run.returncode, data


def unproven(data):
    return sorted({(f["kind"], f["line"], f["name"]) for f in data["findings"]})


for name, minimum in (("call_result_width.elisa", 19), ("returned_call_local.elisa", 9),
                      ("nested_call_results.elisa", 12)):
    code, data = check(name)
    assert code == 0 and data["status"] == "proved", (name, code, data["findings"])
    assert data["findings"] == [], (name, data["findings"])
    assert data["replay"]["certificates"] >= minimum, (name, data["replay"])

code, data = check("rejected_call_result_width.elisa")
assert code == 1 and data["status"] == "failed", code
assert unproven(data) == [
    ("ensure-unproven", 24, "signed_wraps"),
    ("ensure-unproven", 29, "unsigned_wraps"),
    ("ensure-unproven", 35, "off_by_one"),
    ("ensure-unproven", 36, "off_by_one"),
    ("ensure-unproven", 41, "direct_call_off_by_one"),
    ("ensure-unproven", 48, "impure_call_untyped"),
], unproven(data)

code, data = check("rejected_returned_call_local.elisa")
assert code == 1 and data["status"] == "failed", code
assert unproven(data) == [
    ("call-requires-unproven", 36, "unproven_precondition"),
    ("ensure-unproven", 23, "stronger_than_the_summary"),
    ("ensure-unproven", 31, "referenced_value_must_not_survive"),
    ("ensure-unproven", 37, "unproven_precondition"),
], unproven(data)

code, data = check("rejected_nested_call_results.elisa")
assert code == 1 and data["status"] == "failed", code
assert unproven(data) == [
    ("ensure-unproven", 13, "distinct_inner"),
    ("ensure-unproven", 20, "strict_claim"),
    ("ensure-unproven", 26, "reversed_chain"),
    ("ensure-unproven", 32, "swapped_arguments"),
], unproven(data)

print("call results: returned locals keep their summary, constants typed at the call's width, nested calls generalized, replayed")
