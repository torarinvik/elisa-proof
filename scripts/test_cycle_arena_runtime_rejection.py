"""Execute the cyclic-arena adversary and check the API returns rejection."""

from pathlib import Path
import os
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
COMPILER_ROOT = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler"))
STAGE1_WRAPPER = COMPILER_ROOT / "scripts" / "elisac_stage1.sh"
FRESHNESS_CHECK = COMPILER_ROOT / "scripts" / "assert_stage1_fresh.sh"
STAGE1 = COMPILER_ROOT / "bin" / "elisac-stage1"
RUNTIME = COMPILER_ROOT / "build" / "runtime" / "elisacore_runtime.o"
TARGET_FIXTURE = ROOT / "examples" / "rejected_kernel_arena_cycle.elisa"
MUTATION_FIXTURE = ROOT / "examples" / "cycle_arena_runtime_rejection.elisa"


def run(command, **kwargs):
    return subprocess.run(command, text=True, capture_output=True, check=False, **kwargs)


fresh = run(["bash", str(FRESHNESS_CHECK), str(STAGE1)], cwd=COMPILER_ROOT)
assert fresh.returncode == 0, fresh.stderr[-2000:]
assert STAGE1_WRAPPER.is_file() and STAGE1.is_file()
assert RUNTIME.is_file(), f"Stage1 runtime object missing: {RUNTIME}"

with tempfile.TemporaryDirectory(prefix="elisa-cycle-arena-", dir=ROOT / "examples") as temporary:
    temporary = Path(temporary)
    env = dict(os.environ)
    env["ELISA_STAGE1_ROOT"] = str(COMPILER_ROOT)
    env["ELISA_RUNTIME_OBJ"] = str(RUNTIME)

    # Compile the actual target function from the proof fixture with its proof-only block
    # removed (the compiler currently cannot discharge that unrelated imported-helper proof).
    # Then call that exact function at runtime, so the assertion observes its cycle verdict.
    target_source = TARGET_FIXTURE.read_text(encoding="utf-8")
    proof_block = "    proof true:\n        assert 1 == 1\n"
    assert target_source.count(proof_block) == 1
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".elisa", prefix=".cycle-target-",
        dir=ROOT / "examples", delete=False,
    ) as handle:
        executable_source = Path(handle.name)
        handle.write(
            target_source.replace(proof_block, "")
            + "\ndef main() -> i32:\n    return 0 if rejected_cycle_arena() else 1\n"
        )
    target_executable = temporary / "target-cycle-rejection"
    try:
        compiled = run(
            ["bash", str(STAGE1_WRAPPER), "-emit", "exe", "-O2", "-o", str(target_executable), str(executable_source)],
            cwd=ROOT,
            env=env,
        )
    finally:
        executable_source.unlink(missing_ok=True)
    assert compiled.returncode == 0, compiled.stderr[-3000:]
    executed = run([str(target_executable)], cwd=ROOT)
    assert executed.returncode == 0, (
        "rejected_cycle_arena must return true for the self-cycle; "
        f"runtime returned {executed.returncode}: {executed.stderr[-1000:]}"
    )

    # Mutation controls: a valid acyclic arena remains admissible, while a two-node cycle is
    # refused. This makes a constant-false validator fail the same focused gate.
    mutation_executable = temporary / "cycle-mutation-controls"
    compiled = run(
        ["bash", str(STAGE1_WRAPPER), "-emit", "exe", "-O2", "-o", str(mutation_executable), str(MUTATION_FIXTURE)],
        cwd=ROOT,
        env=env,
    )
    assert compiled.returncode == 0, compiled.stderr[-3000:]
    executed = run([str(mutation_executable)], cwd=ROOT)
    assert executed.returncode == 0, (
        "arena admission mutation controls failed (valid DAG accepted, self/two-node cycles "
        f"rejected); runtime returned {executed.returncode}: {executed.stderr[-1000:]}"
    )

print("cyclic arena: target rejects self-cycle; valid DAG accepted; two-node cycle rejected")
