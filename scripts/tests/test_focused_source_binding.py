"""Focused reports must source-bind selected goals and ignore unrequested declarations."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
HARNESS = Path(os.environ.get("ELISA_FOCUSED_SOURCE_BINDING_HARNESS", ""))
SOURCE = ROOT / "examples/function_focus_source_binding.elisa"


def run(function: str, source: Path = SOURCE) -> tuple[subprocess.CompletedProcess[str], dict]:
    result = subprocess.run(
        [str(BINARY), "--function-json", function, str(source)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return result, json.loads(result.stdout)


assert BINARY.is_file(), f"proof executable not found: {BINARY}"
assert HARNESS.is_file(), f"focused source-binding harness not found: {HARNESS}"
direct_api = subprocess.run([str(HARNESS)], capture_output=True, timeout=30)
assert direct_api.returncode == 0, (
    "direct source-admission invariants accepted a replayed goal that differs from the selected "
    f"source postcondition or rejected its positive control: {direct_api.returncode}, "
    f"{direct_api.stderr[:500]!r}"
)

positive_run, positive = run("focused_source_binding_target")
assert positive_run.returncode == 0 and positive["status"] == "proved", positive
assert positive["summary"]["semantic_errors"] == 0, positive["summary"]
assert positive["replay"]["gaps"] == 0
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0
details = {item["name"]: item for item in positive["declaration_details"] if item["kind"] == "function"}
assert details["focused_source_binding_target"]["verified"] is True, details
assert details["focused_source_binding_unrequested"]["verification_reason"] == "not-requested", details

parameter_run, parameter = run("focused_source_binding_parameter_target")
assert parameter_run.returncode == 0 and parameter["status"] == "proved", parameter
assert parameter["summary"]["semantic_errors"] == 0, parameter["summary"]
assert parameter["replay"]["gaps"] == 0
assert parameter["replay"]["certificates"] == parameter["replay"]["replayed"] > 0

open_parameter_run, open_parameter = run(
    "focused_source_binding_parameter_open",
    ROOT / "examples/function_focus_source_binding_open.elisa",
)
assert open_parameter_run.returncode == 1 and open_parameter["status"] == "failed", open_parameter
assert open_parameter["summary"]["unproven"] > 0, open_parameter["summary"]
assert not any(
    item["kind"] == "source-obligation-inventory" and item["status"] == "unsupported"
    for item in open_parameter["findings"]
), open_parameter["findings"]

# Whole-source JSON reporting uses the independent inventory path rather than the focused
# coverage walk, so keep a one-function control for the same parameter-return binding.
whole_parameter_run = subprocess.run(
    [str(BINARY), "--json", str(ROOT / "examples/source_parameter_return_inventory.elisa")],
    capture_output=True,
    text=True,
    timeout=60,
    check=False,
)
whole_parameter = json.loads(whole_parameter_run.stdout)
assert whole_parameter_run.returncode == 0 and whole_parameter["status"] == "proved", whole_parameter
assert whole_parameter["replay"]["gaps"] == 0
assert whole_parameter["replay"]["certificates"] == whole_parameter["replay"]["replayed"] > 0

unsupported_run, unsupported = run("focused_source_binding_unrequested")
assert unsupported_run.returncode == 1 and unsupported["status"] == "failed", unsupported
assert unsupported["verification_state"] == "unsupported", unsupported
assert any(
    item["kind"] == "source-obligation-inventory" and item["status"] == "unsupported"
    for item in unsupported["findings"]
), unsupported["findings"]

assert_by_run = subprocess.run(
    [str(BINARY), "--function-json", "prove_nonnegative", str(ROOT / "examples/verified.elisa")],
    capture_output=True,
    text=True,
    timeout=60,
    check=False,
)
assert assert_by_run.returncode == 0, (assert_by_run.returncode, assert_by_run.stderr)
assert_by_report = json.loads(assert_by_run.stdout)
assert assert_by_report["status"] == "proved", assert_by_report
assert assert_by_report["replay"]["gaps"] == 0

print("focused source admission: literal and parameter returns bind to replay, open goals remain supported, unsupported targets refuse, unrequested declarations are skipped")
