"""Build test-only replay harnesses without widening production helper visibility."""

import json
from pathlib import Path
import re
import subprocess
import tempfile


def _test_replay_includes(root: Path, scratch: Path) -> str:
    replay_file = root / "src/proof/replay.elisa"
    private_helpers = {
        (root / "src/proof/replay/source_binding_validation.elisa").resolve(): "source_binding_validation_test.elisa",
        (root / "src/proof/replay/source_binding_validation/typed_return_constants.elisa").resolve(): "typed_return_constants_test.elisa",
        (root / "src/proof/replay/source_binding_validation/immutable_bindings.elisa").resolve(): "immutable_bindings_test.elisa",
    }
    includes = re.findall(r'^include "([^"]+)"$', replay_file.read_text(encoding="utf-8"), re.MULTILINE)
    if not includes:
        raise AssertionError(f"no replay modules found in {replay_file}")

    expanded = []
    copied_helpers = set()
    for include in includes:
        original = (replay_file.parent / include).resolve()
        if original in private_helpers:
            source = original.read_text(encoding="utf-8")
            private_label = "    private:"
            if source.count(private_label) != 1:
                raise AssertionError(f"expected one private section in {original}")
            # These generated copies are used only by this standalone test executable. The real
            # source remains private, and the test-only visibility change is never linked into
            # either product binary.
            generated = scratch / private_helpers[original]
            # Relocation must preserve the directory used to resolve each include.
            source = re.sub(
                r'^include "([^"\n]+)"$',
                lambda match: f'include "{(original.parent / match.group(1)).resolve().as_posix()}"',
                source,
                flags=re.MULTILINE,
            )
            generated.write_text(source.replace(private_label, "    public:", 1), encoding="utf-8")
            original = generated
            copied_helpers.add(original.name)
        if not original.is_file():
            raise AssertionError(f"replay include does not exist: {original}")
        expanded.append(f'include "{original.as_posix()}"')

    if copied_helpers != set(private_helpers.values()):
        raise AssertionError(f"replay source-binding helpers were not both included: {copied_helpers}")
    return "\n".join(expanded)


def run_source_binding_replay_harness(
    root: Path,
    fixture: Path,
    compiler_root: Path,
    pinned_frontend_revision: str,
    replay_harness: str,
) -> str:
    stage1 = compiler_root / "bin/elisac-stage1"
    stage1_wrapper = compiler_root / "scripts/elisac_stage1.sh"
    freshness_script = compiler_root / "scripts/assert_stage1_fresh.sh"
    frontend_snapshot = root / "build/snapshot/Elisa-compiler"
    if not stage1_wrapper.is_file() or not stage1.is_file() or not freshness_script.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {compiler_root}")
    if not frontend_snapshot.is_dir() or not (frontend_snapshot / ".rev").is_file():
        raise SystemExit(f"pinned frontend snapshot is missing: {frontend_snapshot}; build the proof project first")
    snapshot_revision = (frontend_snapshot / ".rev").read_text(encoding="utf-8").strip()
    if snapshot_revision != pinned_frontend_revision:
        raise SystemExit(
            f"pinned frontend snapshot mismatch: snapshot={snapshot_revision} expected={pinned_frontend_revision}"
        )
    freshness = subprocess.run(
        ["bash", str(freshness_script), str(stage1)],
        capture_output=True,
        text=True,
        cwd=compiler_root,
    )
    if freshness.returncode:
        raise AssertionError(f"Stage1 freshness check failed:\n{freshness.stdout}\n{freshness.stderr}")

    baseline_source = fixture.read_text(encoding="utf-8")
    sources = {
        "__BASELINE_SOURCE__": baseline_source,
        "__WIDENING_SOURCE__": (root / "examples/widening_cast.elisa").read_text(encoding="utf-8"),
        "__SHADOWED_LOCAL_SOURCE__": (root / "test/repro/audit_local_binding_global_shadow.elisa").read_text(encoding="utf-8"),
        "__CUSTOM_CAST_SOURCE__": (root / "test/repro/audit_local_binding_custom_cast.elisa").read_text(encoding="utf-8"),
        "__OVERLOADED_OPERATOR_SOURCE__": (root / "test/repro/audit_local_binding_overloaded_operator.elisa").read_text(encoding="utf-8"),
        "__BINDING_SINK_SOURCE__": (root / "test/repro/audit_local_binding_sink_adversarial.elisa").read_text(encoding="utf-8"),
        "__NESTED_BUILTIN_SOURCE__": (root / "test/repro/audit_local_binding_nested_builtin_positive.elisa").read_text(encoding="utf-8"),
        "__SIMPLE_LOCAL_BINDING_SOURCE__": (root / "test/repro/audit_local_binding_simple_positive.elisa").read_text(encoding="utf-8"),
        "__TYPED_RETURN_SOURCE__": (root / "examples/typed_return_constant.elisa").read_text(encoding="utf-8"),
        "__FALSE_INVARIANT_SOURCE__": baseline_source.replace("invariant rounds <= limit", "invariant rounds < limit", 1),
        "__OVERRUN_SOURCE__": baseline_source.replace("rounds <- rounds + 1", "rounds <- rounds + 2", 1),
        "__STALE_INITIALIZER_SOURCE__": baseline_source.replace(
            "rounds: mutable usize = 0\n    while rounds < limit",
            "rounds: mutable usize = 4\n    while rounds < limit",
            1,
        ),
        "__STALE_REBIND_SOURCE__": baseline_source.replace("rounds <- rounds + 1", "rounds <- rounds + 2", 1),
        "__SHADOWED_PARAMETER_SOURCE__": baseline_source.replace(
            "def bounded_counter(limit: usize)", "def bounded_counter(rounds: usize, limit: usize)", 1
        ),
        "__SHADOWED_GLOBAL_SOURCE__": baseline_source.replace(
            "# A while loop with a counter bounded by a parameter.", "const rounds: usize = 99", 1
        ),
        "__UNRELATED_INVARIANT_SOURCE__": baseline_source.replace("invariant rounds <= limit", "invariant rounds < limit", 1),
    }
    if any(source == baseline_source for marker, source in sources.items() if marker != "__BASELINE_SOURCE__"):
        raise AssertionError("a source-binding mutation did not change its fixture")

    with tempfile.TemporaryDirectory(prefix="source-binding-replay-support-") as scratch_name:
        scratch = Path(scratch_name)
        harness = replay_harness
        for marker, source in sources.items():
            harness = harness.replace(marker, json.dumps(source))
        harness = harness.replace(
            'include "../src/proof/replay.elisa"', _test_replay_includes(root, scratch)
        )
        harness = harness.replace(str(frontend_snapshot), str(frontend_snapshot.resolve()))

        with tempfile.TemporaryDirectory(prefix="bounded-counter-source-replay-", dir=root / "examples") as temporary:
            directory = Path(temporary)
            source_path = directory / "bounded_counter_source_replay.elisa"
            executable = directory / "bounded_counter_source_replay"
            harness = harness.replace("../../Elisa-compiler/", str(frontend_snapshot.resolve()) + "/").replace(
                'include "../src/', 'include "../../src/'
            )
            source_path.write_text(harness, encoding="utf-8")
            compiled = subprocess.run(
                [str(stage1_wrapper), "-emit", "exe", "-O0", "-o", str(executable), str(source_path)],
                capture_output=True,
                text=True,
                cwd=root,
                # This standalone harness embeds the pinned parser and proof replay modules;
                # Stage1 can take longer than the product build on a busy validation host.
                timeout=2400,
            )
            if compiled.returncode:
                raise AssertionError(
                    f"fresh Stage1 source-binding harness failed:\n{compiled.stdout}\n{compiled.stderr}"
                )
            result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=120)
            if result.returncode:
                raise AssertionError(
                    f"source-binding harness returned {result.returncode}: {result.stdout}\n{result.stderr}"
                )
    return freshness.stdout.strip()
