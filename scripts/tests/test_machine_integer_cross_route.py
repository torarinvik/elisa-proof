"""R-042 cross-route regression for suffix metadata vs source integer typing.

The compiler retains legacy numeric suffixes for diagnostics, but they are not
expression types. This test compares actual Stage1 execution with source import,
producer/decision, kernel certificate replay, and portable package replay. It also
runs the kernel's bounded exhaustive u8 add/sub differential fixture.
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
TIMEOUT_SECONDS = 90
OUTPUT_LIMIT = 8 * 1024 * 1024

SOURCE = """\
def imported_suffix_wrap_claim() -> void:
    proof 255u8 + 1u8 == 0u8:
        assert 255u8 + 1u8 == 0u8

def imported_suffix_safe_boundary() -> void:
    proof 254u8 + 1u8 == 255u8:
        assert 254u8 + 1u8 == 255u8

# These literals have no suffix. The declared parameter and return types
# provide the signed i8 context for the arithmetic expressions.
def contextual_i8_add(value: i8) -> i8:
    requires value == 126
    ensure result == 127
    return value + 1

def contextual_i8_square(value: i8) -> i8:
    requires value >= -2
    requires value <= 2
    ensure result >= 0
    return value * value
"""


def run(command, *, cwd=ROOT, env=None, label):
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                text=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as error:
        raise AssertionError(f"R-042 {label} timed out after {TIMEOUT_SECONDS}s") from error
    output_size = len(result.stdout.encode("utf-8")) + len(result.stderr.encode("utf-8"))
    assert output_size <= OUTPUT_LIMIT, f"R-042 {label} exceeded {OUTPUT_LIMIT} output bytes"
    return result


def resolve_pair():
    resolved = run(
        [sys.executable, str(ROOT / "scripts/verify_product_pair.py"), "resolve",
         "--generation-root", str(GENERATION_ROOT)],
        label="matched build resolution",
    )
    assert resolved.returncode == 0, resolved.stderr[-2000:]
    pair = json.loads(resolved.stdout)
    generation = pair["pair_generation"]
    products = pair["products"]
    proof = Path(products["elisa-proof"]["binary"])
    replay = Path(products["elisa-proof-replay"]["binary"])
    proof_manifest = json.loads(Path(products["elisa-proof"]["manifest"]).read_text())
    replay_manifest = json.loads(Path(products["elisa-proof-replay"]["manifest"]).read_text())
    assert proof_manifest["pair_generation"] == replay_manifest["pair_generation"] == generation
    assert proof_manifest["proof"] == replay_manifest["proof"]

    compiler = proof_manifest["compiler"]
    compiler_product = Path(compiler["product"]["path"])
    runtime = Path(proof_manifest["runtime"]["path"])
    assert compiler["stage"] == "stage1" and compiler["stage1_revision"]
    assert hashlib.sha256(compiler_product.read_bytes()).hexdigest() == compiler["product"]["sha256"]
    assert hashlib.sha256(runtime.read_bytes()).hexdigest() == proof_manifest["runtime"]["sha256"]
    assert hashlib.sha256(proof.read_bytes()).hexdigest() == products["elisa-proof"]["binary_sha256"]
    assert hashlib.sha256(replay.read_bytes()).hexdigest() == products["elisa-proof-replay"]["binary_sha256"]
    compiler_root = compiler_product.parent.parent
    assert (compiler_root / "SNAPSHOT").is_file()
    return generation, proof, replay, compiler_product, compiler_root, compiler, proof_manifest


def tactic_result(binary, source, goal, accepted, directory, env):
    bound = run([str(binary), "--goal", str(goal["goal_id"]), str(source)],
                env=env, label=f"goal fingerprint for {goal['name']}")
    assert bound.returncode == 0, bound.stderr[-1000:]
    fingerprint = json.loads(bound.stdout)["goal_fingerprint"]
    script = directory / f"tactic-{goal['name']}.json"
    script.write_text(json.dumps({
        "format": "elisa-proof-tactics-v1",
        "target": {"goal_id": goal["goal_id"], "goal_fingerprint": fingerprint["value"]},
        "actions": [{"action": "decide", "accepted": accepted}],
    }), encoding="utf-8")
    tactic = run([str(binary), "--tactics", str(script), str(source)], env=env,
                 label=f"decide tactic for {goal['name']}")
    report = json.loads(tactic.stdout)
    assert report["source_goal_binding"]["fingerprint_match"] is True, report
    assert report["tactic"]["valid"] is True, report
    assert report["tactic"]["solved"] is accepted, report
    if accepted:
        assert report["tactic"]["kernel_trace_replayed"] is True, report
        assert report["tactic"]["certificate_replayed"] is True, report
    return report


generation, proof_binary, replay_binary, compiler_product, compiler_root, compiler_identity, manifest = resolve_pair()
env = dict(os.environ)
env["ELISA_PROOF_BIN"] = str(proof_binary)
env["ELISA_PROOF_REPLAY_BIN"] = str(replay_binary)
env["ELISA_PROOF_GENERATION_ROOT"] = str(GENERATION_ROOT)

with tempfile.TemporaryDirectory(prefix="elisa-r042-cross-route-") as temporary:
    directory = Path(temporary)
    source = directory / "suffix-import.elisa"
    source.write_text(SOURCE, encoding="utf-8")

    # Independently execute contextual signed arithmetic with unsuffixed literals
    # and declared i8 parameter/results.
    runtime_source = directory / "source-runtime.elisa"
    runtime_source.write_text(
        "def contextual_add(value: i8) -> i8:\n"
        "    return value + 1\n"
        "def contextual_square(value: i8) -> i8:\n"
        "    return value * value\n"
        "def main() -> i32:\n"
        "    return 0 if contextual_add(126) == 127 and contextual_square(10) == 100 and not (255u8 + 1u8 == 0u8) else 1\n",
        encoding="utf-8",
    )
    executable = directory / "source-runtime"
    compiled = run([str(compiler_product), "-emit", "exe", "-O2", "-o", str(executable),
                    str(runtime_source)], cwd=compiler_root, label="source runtime compile")
    assert compiled.returncode == 0, compiled.stderr[-2000:]
    executed = run([str(executable)], label="source runtime evaluation")
    assert executed.returncode == 0, (
        "the compiler must execute in-range signed i8 addition and multiplication while "
        f"keeping the suffix-only expression false; got {executed.returncode}"
    )

    report_run = run([str(proof_binary), "--json", str(source)], env=env,
                     label="source import and producer")
    report = json.loads(report_run.stdout)
    assert report["summary"]["semantic_errors"] == 0, report.get("semantic_diagnostics")
    assert report["replay"]["gaps"] == 0, report["replay"]
    goals = [goal for goal in report["goals"] if goal["rule"] == "goal"]
    false_claim = [goal for goal in goals if goal["name"] == "imported_suffix_wrap_claim"]
    safe_claim = [goal for goal in goals if goal["name"] == "imported_suffix_safe_boundary"]
    contextual_add = [goal for goal in goals if goal["name"] == "contextual_i8_add"]
    contextual_square = [goal for goal in goals if goal["name"] == "contextual_i8_square"]
    assert len(false_claim) == len(safe_claim) == 2, goals
    assert all(not goal["proven"] and goal["replay_status"] != "replayed" for goal in false_claim), false_claim
    assert all(goal["proven"] and goal["replay_status"] == "replayed" for goal in safe_claim), safe_claim
    assert contextual_add and all(goal["proven"] and goal["replay_status"] == "replayed" for goal in contextual_add), contextual_add
    assert contextual_square and all(goal["proven"] and goal["replay_status"] == "replayed" for goal in contextual_square), contextual_square
    assert report["replay"]["certificates"] == report["replay"]["replayed"], report["replay"]

    # Exercise the untrusted decision tactic against the very same source-bound
    # propositions; the false wrap claim must not regain acceptance through tactics.
    tactic_result(proof_binary, source, false_claim[0], False, directory, env)
    tactic_result(proof_binary, source, safe_claim[0], True, directory, env)
    tactic_result(proof_binary, source, contextual_add[0], True, directory, env)
    tactic_result(proof_binary, source, contextual_square[0], True, directory, env)

    package_source = directory / "safe-package.elisa"
    package_source.write_text(
        "def package_safe_boundary() -> void:\n"
        "    proof 254u8 + 1u8 == 255u8:\n"
        "        assert 254u8 + 1u8 == 255u8\n"
        "def package_contextual_signed(value: i8) -> i8:\n"
        "    requires value == 126\n"
        "    ensure result == 127\n"
        "    return value + 1\n"
        "def package_contextual_square(value: i8) -> i8:\n"
        "    requires value >= -2\n"
        "    requires value <= 2\n"
        "    ensure result >= 0\n"
        "    return value * value\n",
        encoding="utf-8",
    )
    package_run = run([str(proof_binary), "--package", str(package_source)], env=env,
                      label="safe theorem package export")
    package = json.loads(package_run.stdout)
    theorem_names = {item["name"] for item in package["theorems"] if item["rule"] == "goal"}
    assert {"package_safe_boundary", "package_contextual_signed", "package_contextual_square"} <= theorem_names, theorem_names
    package_path = directory / "safe-package.json"
    package_path.write_text(package_run.stdout, encoding="utf-8")
    portable = run([str(replay_binary), str(package_path)], env=env,
                   label="portable package replay")
    portable_result = json.loads(portable.stdout)
    assert portable_result["status"] == "replayed", portable_result
    assert portable_result["summary"]["not_replayed"] == 0, portable_result

    rejected_package_run = run([str(proof_binary), "--package", str(source)], env=env,
                               label="false-claim package export")
    rejected_package = json.loads(rejected_package_run.stdout)
    rejected_theorems = {item["name"] for item in rejected_package.get("theorems", [])
                         if item["rule"] == "goal"}
    assert "imported_suffix_wrap_claim" not in rejected_theorems, rejected_package

    # This existing kernel fixture exhaustively compares every pair of u8 values
    # for typed modular addition/subtraction against a wider-integer oracle.
    kernel_executable = directory / "typed-kernel-exhaustive"
    kernel_compile = run(
        [str(compiler_product), "-emit", "exe", "-O2", "-o", str(kernel_executable),
         str(ROOT / "examples/kernel_typed_literals_runtime.elisa")],
        cwd=compiler_root, label="exhaustive typed-kernel compile",
    )
    assert kernel_compile.returncode == 0, kernel_compile.stderr[-2000:]
    kernel_run = run([str(kernel_executable)], label="exhaustive typed-kernel execution")
    assert kernel_run.returncode == 0, kernel_run.returncode

print(
    "R-042 cross-route: compiler rejects suffix-as-u8 overflow interpretation; "
    "producer/tactic refuse it, contextual signed add/multiply source and package replay pass, "
    "and exhaustive typed-u8 "
    f"kernel arithmetic passes ({generation}; Stage1 {compiler_identity['stage1_revision']}; "
    f"compiler {compiler_identity['product']['sha256']}; runtime {manifest['runtime']['sha256']})"
)
