"""Compile the source-level producer/replay probe with the freshness-checked Stage1 toolchain.

This deliberately does not execute build/elisa-proof or build/elisa-proof-replay: they can be
from different source snapshots. The temporary Elisa executable includes the current checker
and replay modules directly, then forges in-memory function-summary and deterministic-call traces.
"""

from pathlib import Path
import os
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
COMPILER_ROOT = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler"))
STAGE1 = COMPILER_ROOT / "bin" / "elisac-stage1"
STAGE1_WRAPPER = COMPILER_ROOT / "scripts" / "elisac_stage1.sh"
FRESHNESS_CHECK = COMPILER_ROOT / "scripts" / "assert_stage1_fresh.sh"
OPT_LEVEL = os.environ.get("ELISA_REPLAY_TEST_OPT_LEVEL", "O2")
BUILD_TIMEOUT_SECONDS = int(os.environ.get("ELISA_REPLAY_TEST_BUILD_TIMEOUT_SECONDS", "300"))


HARNESS_SUPPORT = (ROOT / "scripts/tests/fixtures/call_replay_harness_support.elisa").read_text(encoding="utf-8")
HARNESS_MAIN = (ROOT / "scripts/tests/fixtures/call_replay_harness_main.elisa").read_text(encoding="utf-8")


def main() -> None:
    if not STAGE1_WRAPPER.is_file() or not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {COMPILER_ROOT}")
    subprocess.run(["bash", str(FRESHNESS_CHECK), str(STAGE1)], check=True, cwd=COMPILER_ROOT)

    with tempfile.TemporaryDirectory(prefix="qualified-call-replay-", dir=ROOT / "examples") as temporary:
        directory = Path(temporary)
        source = directory / "qualified_call_replay.elisa"
        executable = directory / "qualified_call_replay"
        compiler_include = str(COMPILER_ROOT.resolve()) + "/"
        harness = (HARNESS_SUPPORT + "\n" + HARNESS_MAIN).replace("../../Elisa-compiler/", compiler_include).replace(
            'include "../src/', 'include "../../src/'
        )
        source.write_text(harness, encoding="utf-8")
        compiled = subprocess.run(
            [str(STAGE1_WRAPPER), "-emit", "exe", f"-{OPT_LEVEL}", "-o", str(executable), str(source)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=BUILD_TIMEOUT_SECONDS,
        )
        if compiled.returncode:
            raise AssertionError(f"fresh Stage1 harness compile failed:\n{compiled.stdout}\n{compiled.stderr}")
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
        mixed_overload = directory / "mixed_internal_extern.elisa"
        mixed_object = directory / "mixed_internal_extern.o"
        mixed_overload.write_text(
            "def mixed_internal_extern(x: i64) -> i64:\n    return x\n\n"
            "extern mixed_internal_extern(x: i64, y: i64) -> i64\n",
            encoding="utf-8",
        )
        overload_compile = subprocess.run(
            [str(STAGE1_WRAPPER), "-emit", "obj", "-O2", "-o", str(mixed_object), str(mixed_overload)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=BUILD_TIMEOUT_SECONDS,
        )
        assert overload_compile.returncode == 0, (
            "the same-name internal/extern overload premise must compile:\n"
            f"{overload_compile.stdout}\n{overload_compile.stderr}"
        )
        print("qualified call-summary replay: assignment RHS and safe branch joins replay; stale call-to-call, branch-join, if-return and multi-arm match claims are refused by producer and replay; forged arguments, spans, wrong modules, overloads and nested-call reductions are refused")


if __name__ == "__main__":
    main()
