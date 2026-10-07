"""A builtin integer cast has a primitive result type; an omitted bound stays refused."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
def run_source(name):
    source = ROOT / "examples" / name
    run = subprocess.run([str(BINARY), "--json", str(source)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 1, (name, run.returncode, run.stderr, run.stdout)
    report = json.loads(run.stdout)
    assert report["summary"]["semantic_errors"] == 0, (name, report)
    assert report["replay"]["gaps"] == 0, (name, report)
    assert report["replay"]["certificates"] == report["replay"]["replayed"], (name, report)
    functions = {
        declaration["name"]: declaration
        for declaration in report["declaration_details"]
        if declaration.get("kind") == "function"
    }
    return report, functions


report, functions = run_source("count_cast_summary.elisa")
assert functions["terminated"]["verified"], functions["terminated"]
for refused in ("missing_upper_guard", "cast_value_is_not_its_receiver",
                "cast_range_is_not_its_receiver_range"):
    assert not functions[refused]["verified"], functions[refused]

_, functions = run_source("count_cast_custom_hook_refusal.elisa")
assert not functions["custom_hook_is_not_builtin_cast"]["verified"], functions

_, functions = run_source("count_cast_float_refusal.elisa")
assert not functions["floating_result_is_not_integer_witness"]["verified"], functions
assert not functions["integer_cast_does_not_preserve_float_value"]["verified"], functions

_, functions = run_source("rejected_shadowed_conversion_conditional.elisa")
assert not functions["shadowed_method_is_not_a_conversion"]["verified"], functions

_, functions = run_source("rejected_builtin_type_named_function.elisa")
assert not functions["rejected_cast_is_not_the_shadowing_function"]["verified"], functions
print("integer cast type witness is bounded; value, float, hook, and shadowing controls refuse")
