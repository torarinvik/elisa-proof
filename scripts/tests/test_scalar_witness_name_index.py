"""Differentially exercise the scalar-witness name index with a fresh Stage1 compiler."""

from pathlib import Path
import os
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
COMPILER_ROOT = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler"))
STAGE1 = COMPILER_ROOT / "bin" / "elisac-stage1"
FRESHNESS_CHECK = COMPILER_ROOT / "scripts" / "assert_stage1_fresh.sh"
FIXTURE = ROOT / "test" / "repro" / "scalar_witness_name_index.elisa"


def fnv1a_u32(text: str) -> int:
    value = 2166136261
    for byte in text.encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


def run(*command: str, cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    if fnv1a_u32("r019-s6WXBpYWBJfn") != fnv1a_u32("r019-u22pK2GiCukM"):
        raise SystemExit("R-019 collision fixture no longer contains an exact FNV-1a collision")
    if not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"fresh Stage1 compiler unavailable under {COMPILER_ROOT}")

    # Fail closed on a stale binary; a locally available but unmatched Stage1 is not evidence.
    run(str(FRESHNESS_CHECK), str(STAGE1), cwd=COMPILER_ROOT)

    runtime = COMPILER_ROOT / "build" / "runtime" / "elisacore_runtime.o"
    hooks_source = COMPILER_ROOT / "test" / "parity" / "profile_hooks.c"
    clang = os.environ.get("CLANG", "clang")
    if not runtime.is_file() or not hooks_source.is_file():
        raise SystemExit("matching Stage1 runtime or profiler-hook source is unavailable")

    with tempfile.TemporaryDirectory(prefix="elisa-r019-stage1-") as temp:
        scratch = Path(temp)
        object_file = scratch / "scalar-witness-index.o"
        hooks_object = scratch / "profile-hooks.o"
        executable = scratch / "scalar-witness-index"
        run(str(STAGE1), "-permissive", "-emit", "obj", "-O0", "-o", str(object_file), str(FIXTURE))
        run(clang, "-c", str(hooks_source), "-o", str(hooks_object))
        run(clang, "-Wl,-dead_strip", "-o", str(executable), str(object_file), str(hooks_object), str(runtime))
        run(str(executable))

    print("R-019 Stage1 indexed-vs-linear oracle passed: full-hash collision, duplicates, shadowed spelling, marker order")


if __name__ == "__main__":
    main()
