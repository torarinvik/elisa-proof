"""Runtime resolution is tested with mocked compilers and never invokes a compiler."""
import os
from pathlib import Path
import subprocess
import tempfile

if not __debug__:
    raise SystemExit("runtime input checks must run without Python -O")
ROOT = Path(__file__).resolve().parents[1]


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"mock")
    path.chmod(0o755)


def resolve(compiler, home, **variables):
    environment = {key: value for key, value in os.environ.items()
                   if key not in ("ELISA_RUNTIME_OBJ", "ELISA_COMPILER_SRC", "ELISA_COMPILER_ROOT")}
    environment.update({"HOME": str(home), **{key: str(value) for key, value in variables.items()}})
    command = (
        'source "$1"; result=0; elisa_resolve_runtime_obj "$2" "$3" || result=$?; '
        'printf "runtime=%s\\n" "${RUNTIME_OBJ:-}"; exit "$result"'
    )
    return subprocess.run(["bash", "-c", command, "runtime-test",
                           str(ROOT / "scripts/runtime_inputs.sh"), str(compiler), "0"],
                          env=environment, capture_output=True, text=True, timeout=5)


def stage1_classification(compiler, home, **variables):
    environment = {key: value for key, value in os.environ.items()
                   if key not in ("ELISA_RUNTIME_OBJ", "ELISA_COMPILER_SRC", "ELISA_COMPILER_ROOT")}
    environment.update({"HOME": str(home), **{key: str(value) for key, value in variables.items()}})
    command = ('source "$1"; elisa_resolve_runtime_obj "$2" 0; '
               'printf "stage1=%s\\n" "$COMPILER_IS_STAGE1"')
    return subprocess.run(["bash", "-c", command, "runtime-test",
                           str(ROOT / "scripts/runtime_inputs.sh"), str(compiler)],
                          env=environment, capture_output=True, text=True, timeout=5)


with tempfile.TemporaryDirectory(prefix="elisa runtime input ") as directory:
    temp = Path(directory)
    source_root = temp / "compiler-source"
    home = temp / "home"
    source_runtime = source_root / "build/runtime/elisacore_runtime.o"
    home_runtime = home / ".elisac/elisacore_runtime.o"
    touch(source_runtime)
    touch(home_runtime)

    # A bare Stage1 binary uses the known checkout runtime, never the installed fallback.
    bare_stage1 = temp / "bin/elisac-stage1"
    touch(bare_stage1)
    run = resolve(bare_stage1, home, ELISA_COMPILER_SRC=source_root)
    assert run.returncode == 0 and run.stdout == f"runtime={source_runtime}\n", (run.stdout, run.stderr)

    # ELISA_COMPILER_ROOT is the canonical override when both source-root spellings exist.
    root_precedence = temp / "root-precedence"
    root_runtime = root_precedence / "build/runtime/elisacore_runtime.o"
    source_alias = temp / "source-alias"
    source_alias_runtime = source_alias / "build/runtime/elisacore_runtime.o"
    touch(root_runtime)
    touch(source_alias_runtime)
    run = resolve(bare_stage1, home, ELISA_COMPILER_ROOT=root_precedence,
                  ELISA_COMPILER_SRC=source_alias)
    assert run.returncode == 0 and run.stdout == f"runtime={root_runtime}\n", (run.stdout, run.stderr)

    # A binary that embeds the freshness-guarded wrapper path keeps that wrapper's root.
    wrapper = source_root / "scripts/elisac_stage1.sh"
    embedded_stage1 = temp / "embedded/elisac-stage1"
    touch(embedded_stage1)
    embedded_stage1.write_text(f"#!/bin/sh\n# wrapper: {wrapper}\n")
    other_root = temp / "other-source"
    other_runtime = other_root / "build/runtime/elisacore_runtime.o"
    touch(other_runtime)
    run = resolve(embedded_stage1, home, ELISA_COMPILER_SRC=other_root)
    assert run.returncode == 0 and run.stdout == f"runtime={source_runtime}\n", (run.stdout, run.stderr)

    # A wrapper continues to use the source tree it names.
    touch(wrapper)
    run = resolve(wrapper, home)
    assert run.returncode == 0 and run.stdout == f"runtime={source_runtime}\n", (run.stdout, run.stderr)

    # A known but incomplete wrapper must not silently borrow the unrelated HOME runtime.
    broken_wrapper_root = temp / "broken wrapper root"
    broken_wrapper = broken_wrapper_root / "scripts/elisac_stage1.sh"
    touch(broken_wrapper)
    run = resolve(broken_wrapper, home)
    expected_wrapper_runtime = broken_wrapper_root / "build/runtime/elisacore_runtime.o"
    assert run.returncode == 2 and run.stdout == "runtime=\n", (run.returncode, run.stdout, run.stderr)
    assert run.stderr == f"Stage1 wrapper runtime object not found: {expected_wrapper_runtime}\n", run.stderr

    # A bare installed compiler keeps its HOME runtime when no source root is known.
    installed_stage1 = temp / "installed/elisac-stage1"
    touch(installed_stage1)
    run = resolve(installed_stage1, home)
    assert run.returncode == 0 and run.stdout == f"runtime={home_runtime}\n", (run.stdout, run.stderr)

    # Unrecognized compiler names remain unclassified, matching compiler provenance logic.
    unknown_compiler = temp / "bin/custom-compiler"
    touch(unknown_compiler)
    unknown = stage1_classification(unknown_compiler, home, ELISA_COMPILER_SRC=source_root)
    assert unknown.returncode == 0 and unknown.stdout == "stage1=0\n", (unknown.stdout, unknown.stderr)

    # Stage0 never acquires an unrelated Stage1 runtime implicitly.
    stage0 = temp / "bin/elisac-stage0"
    touch(stage0)
    command = ('source "$1"; elisa_resolve_runtime_obj "$2" 1; '
               'printf "runtime=%s\\n" "${RUNTIME_OBJ:-}"')
    stage0_run = subprocess.run(["bash", "-c", command, "runtime-test",
                                 str(ROOT / "scripts/runtime_inputs.sh"), str(stage0)],
                                env={k: v for k, v in os.environ.items()
                                     if k not in ("ELISA_RUNTIME_OBJ", "ELISA_COMPILER_SRC",
                                                  "ELISA_COMPILER_ROOT")},
                                capture_output=True, text=True, timeout=5)
    assert stage0_run.returncode == 0 and stage0_run.stdout == "runtime=\n", (stage0_run.stdout, stage0_run.stderr)

    # Explicit valid overrides win; missing or non-file paths fail without falling back.
    override = temp / "explicit/runtime.o"
    touch(override)
    run = resolve(bare_stage1, home, ELISA_COMPILER_SRC=source_root,
                  ELISA_RUNTIME_OBJ=override)
    assert run.returncode == 0 and run.stdout == f"runtime={override}\n", (run.stdout, run.stderr)
    missing = temp / "missing-runtime.o"
    run = resolve(bare_stage1, home, ELISA_COMPILER_SRC=source_root,
                  ELISA_RUNTIME_OBJ=missing)
    assert run.returncode == 2, (run.returncode, run.stdout, run.stderr)
    assert run.stdout == "runtime=\n", run.stdout
    assert run.stderr == "Elisa runtime object not found: %s\n" % missing, run.stderr
    run = resolve(bare_stage1, home, ELISA_COMPILER_SRC=source_root,
                  ELISA_RUNTIME_OBJ=temp)
    assert run.returncode == 2 and run.stdout == "runtime=\n", (run.returncode, run.stdout, run.stderr)

    # A declared source root is authoritative even when its expected runtime is absent.
    missing_root = temp / "missing-source"
    run = resolve(bare_stage1, home, ELISA_COMPILER_SRC=missing_root)
    expected = missing_root / "build/runtime/elisacore_runtime.o"
    assert run.returncode == 2 and run.stdout == "runtime=\n", (run.returncode, run.stdout, run.stderr)
    assert run.stderr == f"Stage1 source runtime object not found: {expected}\n", run.stderr

    # The real build entrypoint rejects an invalid explicit override before invoking its mock.
    missing_override = temp / "missing-build-runtime.o"
    mock_compiler = temp / "mock-bin/elisac-stage1"
    invocation_marker = temp / "compiler-was-invoked"
    mock_compiler.parent.mkdir(parents=True)
    mock_compiler.write_text(f"#!/bin/sh\ntouch '{invocation_marker}'\nexit 99\n")
    mock_compiler.chmod(0o755)
    environment = {key: value for key, value in os.environ.items()
                   if key not in ("ELISA_RUNTIME_OBJ", "ELISA_COMPILER_SRC", "ELISA_COMPILER_ROOT")}
    environment.update(ELISA_COMPILER_BIN=str(mock_compiler), ELISA_RUNTIME_OBJ=str(missing_override),
                       ELISA_PROOF_PRODUCTS="one")
    build = subprocess.run(["bash", str(ROOT / "scripts/build.sh")], cwd=ROOT,
                           env=environment, capture_output=True, text=True, timeout=10)
    assert build.returncode == 2, (build.returncode, build.stdout, build.stderr)
    assert build.stdout == "", build.stdout
    assert build.stderr == f"Elisa runtime object not found: {missing_override}\n", build.stderr
    assert not invocation_marker.exists(), "invalid explicit runtime invoked the compiler"

print("build runtime inputs: precedence, spaces, wrapper failures, installed, stage0, and unknown cases passed")
