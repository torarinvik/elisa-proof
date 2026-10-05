"""Check safe, explicitly unsafe, opaque and returned-reference alias boundaries."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("alias-boundary checks must run without Python -O")

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def check_function(source_name, function_name, expected_exit, status,
                   finding_kinds, counts, semantic_errors=0):
    source = ROOT / "examples" / source_name
    run = subprocess.run([str(BIN), "--function-json", function_name, str(source)],
                         capture_output=True, text=True, timeout=60)
    report = json.loads(run.stdout)
    summary = report["summary"]
    replay = report["replay"]
    assert run.returncode == expected_exit, (function_name, run.returncode, run.stderr)
    assert report["status"] == status, (function_name, report["status"])
    summary_counts = ("obligations", "proven", "unproven", "semantic_errors",
                      "semantic_diagnostics")
    replay_counts = ("certificates", "replayed", "gaps")
    for label, values, fields in (("summary", summary, summary_counts),
                                  ("replay", replay, replay_counts)):
        for field in fields:
            value = values[field]
            assert type(value) is int and value >= 0, (function_name, label, field, value)
    assert summary["semantic_errors"] == semantic_errors, (function_name, summary)
    assert (summary["obligations"], summary["proven"], summary["unproven"]) == counts
    assert summary["obligations"] == summary["proven"] + summary["unproven"]
    assert [finding["kind"] for finding in report["findings"]] == finding_kinds
    assert replay["certificates"] == replay["replayed"] == summary["proven"]
    assert replay["gaps"] == 0
    assert report["trust"]["trusted_assumptions"] == []
    return report


positive = check_function("alias_boundary_regression.elisa", "nonalias_call_positive",
                          0, "proved", [], (5, 5, 0))
negative = check_function("alias_boundary_regression.elisa", "unsafe_alias_call_negative",
                          1, "failed", ["borrow-call-alias"], (5, 4, 1))
assert negative["findings"][0]["status"] == "unknown"

extern = check_function("alias_boundary_extern_probe.elisa", "raw_extern_alias_call",
                        1, "failed", ["borrow-call-opaque"], (2, 1, 1))
assert extern["findings"][0]["status"] == "unsupported"

unresolved = check_function("alias_boundary_unresolved_probe.elisa", "unresolved_alias_call",
                            1, "failed", ["borrow-call-opaque"], (1, 0, 1), 2)
assert {item["message"] for item in unresolved["semantic_diagnostics"]} == {
    'undefined identifier "undeclared_mutable_pair"',
    'cannot call non-function value of type <invalid>',
}

returned = check_function("alias_boundary_returned_ref_probe.elisa", "intermediary_alias",
                          1, "failed",
                          ["borrow-source-opaque", "call-requires-unproven", "ensure-unproven"],
                          (6, 3, 3))
assert returned["verification_state"] == "unsupported"
print("alias boundary: nonalias 5/5 replayed; Unsafe.Alias, extern, unresolved and returned-ref cases refused; zero replay gaps")
