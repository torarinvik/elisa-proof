"""D3: compare fixed-width source checking, proof reports, and portable replay.

The matrix covers the last representable increment for signed and unsigned 8-bit values,
the immediately overflowing increments, and a small bounded square.  Arithmetic search is
never itself accepted as evidence: every admitted goal must occur in the exported package and
be replayed by the generation-matched portable kernel.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
GENERATION_ROOT = ROOT / "build/elisa-proof-generations"
TIMEOUT_SECONDS = 60
OUTPUT_LIMIT = 8 * 1024 * 1024

SOURCE = """\
def i8_last_safe_increment(x: i8) -> i8:
    requires x == 126
    ensure result == 127
    return x + 1

def u8_last_safe_increment(x: u8) -> u8:
    requires x == 254
    ensure result == 255
    return x + 1

def i8_max_increment_is_strict(x: i8) -> i8:
    requires x == 127
    ensure result > x
    return x + 1

def u8_max_increment_is_strict(x: u8) -> u8:
    requires x == 255
    ensure result > x
    return x + 1

def bounded_i8_square_is_nonnegative(x: i8) -> i8:
    requires x >= -2
    requires x <= 2
    ensure result >= 0
    return x * x

def overflowing_i8_square_is_nonnegative(x: i8) -> i8:
    requires x >= 0
    requires x <= 15
    ensure result >= 0
    return x * x

def unbounded_i8_square_is_nonnegative(x: i8) -> i8:
    ensure result >= 0
    return x * x
"""


def run(command, *, env=None, label):
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                text=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as error:
        raise AssertionError(f"D3 {label} timed out after {TIMEOUT_SECONDS}s: {command[0]}") from error
    output_size = len(result.stdout.encode("utf-8")) + len(result.stderr.encode("utf-8"))
    assert output_size <= OUTPUT_LIMIT, f"D3 {label} output exceeded {OUTPUT_LIMIT} bytes"
    return result


def resolve_pair():
    resolver = run(
        [sys.executable, str(ROOT / "scripts/verify_product_pair.py"), "resolve",
         "--generation-root", str(GENERATION_ROOT)],
        label="product-pair resolution",
    )
    assert resolver.returncode == 0, (
        "D3 requires a current integrity-checked proof/replay generation; resolver refused: "
        + resolver.stderr[-2000:]
    )
    pair = json.loads(resolver.stdout)
    generation = pair["pair_generation"]
    products = pair["products"]
    proof = Path(products["elisa-proof"]["binary"])
    replay = Path(products["elisa-proof-replay"]["binary"])
    proof_manifest_path = Path(products["elisa-proof"]["manifest"])
    replay_manifest_path = Path(products["elisa-proof-replay"]["manifest"])
    proof_manifest = json.loads(proof_manifest_path.read_text(encoding="utf-8"))
    replay_manifest = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
    assert proof_manifest["pair_generation"] == replay_manifest["pair_generation"] == generation
    assert proof_manifest["proof"] == replay_manifest["proof"], "D3 proof/replay source provenance differs"
    assert hashlib.sha256(proof.read_bytes()).hexdigest() == products["elisa-proof"]["binary_sha256"]
    assert hashlib.sha256(replay.read_bytes()).hexdigest() == products["elisa-proof-replay"]["binary_sha256"]

    compiler_info = proof_manifest["compiler"]
    compiler = Path(compiler_info["product"]["path"])
    assert compiler_info["stage"] == "stage1" and compiler_info["stage1_revision"], (
        "D3 source-check compiler provenance is not a Stage1 frontend"
    )
    assert compiler.is_file(), f"D3 matched Stage1 compiler is missing: {compiler}"
    assert hashlib.sha256(compiler.read_bytes()).hexdigest() == compiler_info["product"]["sha256"], (
        "D3 matched Stage1 compiler hash differs from the proof build manifest"
    )
    return generation, proof, replay, compiler


generation, proof_binary, replay_binary, source_compiler = resolve_pair()
isolated_env = dict(os.environ)
isolated_env["ELISA_PROOF_BIN"] = str(proof_binary)
isolated_env["ELISA_PROOF_REPLAY_BIN"] = str(replay_binary)
isolated_env["ELISA_PROOF_GENERATION_ROOT"] = str(GENERATION_ROOT)

with tempfile.TemporaryDirectory(prefix="elisa-d3-fixed-width-") as directory:
    work = Path(directory)
    source = work / "fixed_width_matrix.elisa"
    object_file = work / "fixed_width_matrix.o"
    package_file = work / "fixed_width_matrix.package.json"
    source.write_text(SOURCE, encoding="utf-8")

    # A compiler object emission is the independent parser/type/source check; no linking or
    # runtime behavior is used to infer a proof.
    source_check = run(
        [str(source_compiler), "-emit", "obj", "-O2", "-o", str(object_file), str(source)],
        label="Stage1 source check",
    )
    assert source_check.returncode == 0 and object_file.is_file(), (
        "D3 Stage1 source check rejected the matrix: " + source_check.stderr[-3000:]
    )

    report_run = run([str(proof_binary), "--json", str(source)], env=isolated_env,
                     label="proof report")
    assert report_run.returncode == 1, (report_run.returncode, report_run.stderr[-2000:])
    report = json.loads(report_run.stdout)
    assert report["status"] == "failed", report.get("status")
    assert report["summary"]["semantic_errors"] == 0, report.get("semantic_diagnostics")
    assert report["trust"]["trusted_assumptions"] == [], report["trust"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"] > 0, report["replay"]

    functions = {
        declaration["name"]: declaration
        for declaration in report["declaration_details"]
        if declaration.get("kind") == "function"
    }
    admitted = {"i8_last_safe_increment", "u8_last_safe_increment", "bounded_i8_square_is_nonnegative"}
    refused = {"i8_max_increment_is_strict", "u8_max_increment_is_strict",
               "overflowing_i8_square_is_nonnegative", "unbounded_i8_square_is_nonnegative"}
    assert (admitted | refused) <= functions.keys(), (admitted | refused, functions.keys())
    for name in admitted:
        assert functions[name]["verified"], (name, functions[name])
    for name in refused:
        assert not functions[name]["verified"], (name, functions[name])
    failed_goals = {goal["name"] for goal in report["goals"]
                    if goal["rule"] == "goal" and not goal["proven"]}
    assert refused <= failed_goals, (refused, failed_goals)
    assert report["verification_state"] == "unknown", report["verification_state"]
    refusals = {finding["name"]: finding for finding in report["findings"]
                if finding["name"] in refused and finding["kind"] == "ensure-unproven"}
    assert refused <= refusals.keys(), refusals
    assert all(refusals[name]["status"] == "unknown"
               and not refusals[name]["counterexample_found"] for name in refused), refusals

    package_run = run([str(proof_binary), "--package", str(source)], env=isolated_env,
                      label="portable package export")
    assert package_run.returncode in (0, 1), (package_run.returncode, package_run.stderr[-2000:])
    package_file.write_text(package_run.stdout, encoding="utf-8")
    package = json.loads(package_run.stdout)
    assert package["format"] == "elisa-proof-package-v1" and package["source"]["admissible"], package
    goal_theorem_names = {theorem["name"] for theorem in package["theorems"]
                          if theorem["rule"] == "goal"}
    assert admitted <= goal_theorem_names, (admitted, goal_theorem_names)
    assert not (refused & goal_theorem_names), (
        refused, [(theorem["name"], theorem["rule"]) for theorem in package["theorems"]]
    )

    portable = run([str(replay_binary), str(package_file)], env=isolated_env,
                   label="portable certificate replay")
    assert portable.returncode == 0, (portable.returncode, portable.stderr[-2000:])
    replay_result = json.loads(portable.stdout)
    assert replay_result["format"] == "elisa-proof-replay-result-v1", replay_result
    assert replay_result["status"] == "replayed", replay_result
    assert replay_result["trust"]["kernel"] == "checked", replay_result["trust"]
    assert replay_result["summary"]["theorems"] == len(package["theorems"]), replay_result
    assert replay_result["summary"]["replayed"] == len(package["theorems"]), replay_result
    assert replay_result["summary"]["not_replayed"] == 0, replay_result

print(f"D3 fixed-width matrix: source check, report, and portable replay agree ({generation})")
