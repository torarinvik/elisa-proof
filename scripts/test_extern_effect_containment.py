"""Source-bound extern effect rows grant no arbitrary native result or purity fact."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O")


def run(fixture, code):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == code, (result.returncode, result.stderr)
    report = json.loads(result.stdout)
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    return report, result.stdout, result.stderr


positive, stdout, stderr = run("extern_effect_containment.elisa", 0)
repeated, repeat_stdout, repeat_stderr = run("extern_effect_containment.elisa", 0)
assert stdout == repeat_stdout and stderr == repeat_stderr
assert positive["status"] == "proved" and positive["summary"]["proven"] == positive["summary"]["obligations"]
certified = {g["name"] for g in positive["goals"] if g["rule"] == "effect-containment" and g["proven"]}
assert {"calls_native_row", "calls_explicit_empty_native_row", "calls_both_native_rows"} <= certified
negative, _, _ = run("rejected_extern_effect_containment.elisa", 1)
for name, kind in (("rejected_narrow_native_row", "effect-row-exceeded"),
                   ("rejected_missing_native_row", "effect-call-opaque"),
                   ("rejected_native_result_is_zero", "ensure-unproven")):
    assert any(f["name"] == name and f["kind"] == kind for f in negative["findings"]), (name, negative["findings"])
    assert not any(d.get("name") == name and d.get("verified") for d in negative["declaration_details"])
negative_certified = {g["name"] for g in negative["goals"] if g["rule"] == "effect-containment" and g["proven"]}
assert not negative_certified & {"rejected_narrow_native_row", "rejected_missing_native_row"}
assert "rejected_native_result_is_zero" in negative_certified
print("Complete extern effect rows replay identically; exceeded/missing rows and unknown native results reject")
