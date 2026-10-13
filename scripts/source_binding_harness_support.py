"""Build test-only replay harnesses without widening production helper visibility."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from stage1_provenance_validation import validated_stage1_snapshot_std_root


def checked_in_stage0_revision(root: Path) -> str:
    pinned = (root / "ELISA_STAGE0_REV").read_text(encoding="ascii").strip()
    configured = os.environ.get("ELISA_STAGE0_REV", "").strip()
    if configured and configured != pinned:
        raise ValueError("ELISA_STAGE0_REV environment value differs from the checked-in proof pin")
    return pinned


def _source_file_manifest(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def assert_canonical_std_matches_snapshot(snapshot_std: Path, canonical_std: Path) -> None:
    try:
        snapshot_manifest = _source_file_manifest(snapshot_std)
        canonical_manifest = _source_file_manifest(canonical_std)
    except OSError as error:
        raise ValueError(f"cannot compare pinned and canonical standard libraries: {error}") from error
    if not snapshot_manifest or canonical_manifest != snapshot_manifest:
        raise ValueError(
            f"canonical standard library does not match pinned compiler snapshot: "
            f"{canonical_std} vs {snapshot_std}"
        )


def _test_replay_includes(root: Path, scratch: Path) -> str:
    replay_file = root / "src/proof/replay.elisa"
    private_helpers = {
        (root / "src/proof/replay/differences_and_facts.elisa").resolve(): "differences_and_facts_test.elisa",
        (root / "src/proof/replay/source_binding_validation.elisa").resolve(): "source_binding_validation_test.elisa",
        (root / "src/proof/replay/source_binding_validation/typed_return_constants.elisa").resolve(): "typed_return_constants_test.elisa",
        (root / "src/proof/replay/source_binding_validation/immutable_bindings.elisa").resolve(): "immutable_bindings_test.elisa",
        (root / "src/proof/replay/deterministic_call_sites.elisa").resolve(): "deterministic_call_sites_test.elisa",
        (root / "src/proof/replay/type_bound_loop_scope.elisa").resolve(): "type_bound_loop_scope_test.elisa",
        (root / "src/proof/replay/type_bound_local_rebind.elisa").resolve(): "type_bound_local_rebind_test.elisa",
        (root / "src/proof/replay/type_bound_validation.elisa").resolve(): "type_bound_validation_test.elisa",
        (root / "src/proof/replay/fact_trace_validation.elisa").resolve(): "fact_trace_validation_test.elisa",
        (root / "src/proof/replay/fact_trace_index.elisa").resolve(): "fact_trace_index_test.elisa",
    }
    includes = re.findall(r'^include "([^"]+)"$', replay_file.read_text(encoding="utf-8"), re.MULTILINE)
    if not includes:
        raise AssertionError(f"no replay modules found in {replay_file}")

    copied_helpers = set()

    def rebase_nested_includes(owner: Path, source: str) -> str:
        return re.sub(
            r'^include "([^"]+)"$',
            lambda match: harness_include((owner.parent / match.group(1)).resolve()),
            source,
            flags=re.MULTILINE,
        )

    def harness_include(original: Path) -> str:
        if not original.is_file():
            raise AssertionError(f"replay include does not exist: {original}")
        if original in private_helpers:
            source = original.read_text(encoding="utf-8")
            source = rebase_nested_includes(original, source)
            private_label = "    private:"
            if source.count(private_label) < 1:
                raise AssertionError(f"expected at least one private section in {original}")
            # Only the standalone harness receives these public helper copies. A module may
            # reopen its private section after explanatory documentation or additional helpers.
            generated = scratch / private_helpers[original]
            generated.write_text(source.replace(private_label, "    public:"), encoding="utf-8")
            copied_helpers.add(generated.name)
            original = generated
        elif original == (root / "src/proof/replay/source_call_coverage.elisa").resolve():
            # This facade owns the transitive cast helper include. Rebase all its includes
            # to their original locations while substituting the private helper copy.
            source = original.read_text(encoding="utf-8")
            source = rebase_nested_includes(original, source)
            generated = scratch / "source_call_coverage_test.elisa"
            generated.write_text(source, encoding="utf-8")
            original = generated
        return f'include "{original.as_posix()}"'

    expanded = [harness_include((replay_file.parent / include).resolve()) for include in includes]

    if copied_helpers != set(private_helpers.values()):
        raise AssertionError(f"replay source-binding helpers were not all included: {copied_helpers}")
    return "\n".join(expanded)


def _grant_global_effects_to_harness_calls(source: str) -> str:
    """Add local Global grants to test-only parser and proof API call expressions.

    The proof APIs intentionally carry Global effects. Older standalone replay harnesses omitted
    their local grants. Qualify only their call expressions, leaving the fixture source strings,
    function contracts, and return/control-flow structure untouched.
    """
    code = bytearray(b"\x01") * len(source)
    in_string = False
    in_comment = False
    escaped = False
    for index, char in enumerate(source):
        if in_comment:
            code[index] = 0
            if char == "\n":
                in_comment = False
        elif in_string:
            code[index] = 0
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            code[index] = 0
            in_string = True
        elif char == "#":
            code[index] = 0
            in_comment = True

    wrappers = []
    for match in re.finditer(r"\b(?:frontend_parse|proof_[A-Za-z0-9_]+)\s*\(", source):
        if not all(code[index] for index in range(match.start(), match.end())):
            continue
        line_start = source.rfind("\n", 0, match.start()) + 1
        if re.search(r"\bdef\s+$", source[line_start:match.start()]):
            continue
        open_paren = source.find("(", match.start(), match.end())
        depth = 0
        close_paren = None
        for index in range(open_paren, len(source)):
            if not code[index]:
                continue
            if source[index] == "(":
                depth += 1
            elif source[index] == ")":
                depth -= 1
                if depth == 0:
                    close_paren = index
                    break
        if close_paren is None:
            raise AssertionError(f"unterminated test harness call at offset {match.start()}")
        if re.match(r"\s*can\s+Global\{Read,Write\}", source[close_paren + 1:]):
            continue
        wrappers.append((match.start(), close_paren + 1))

    insertions: dict[int, list[str]] = {}
    for start, end in wrappers:
        insertions.setdefault(start, []).append("(")
        insertions.setdefault(end, []).append(" can Global{Read,Write})")
    pieces = []
    cursor = 0
    for offset in sorted(insertions):
        pieces.append(source[cursor:offset])
        pieces.extend(insertions[offset])
        cursor = offset
    pieces.append(source[cursor:])
    return "".join(pieces)


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
    compiler_env = {
        key: value for key, value in os.environ.items()
        if key != "ELISA_ALLOW_STALE_STAGE1" and key != "ELISA_STAGE0_REV"
    }
    if not stage1_wrapper.is_file() or not stage1.is_file() or not freshness_script.is_file():
        raise SystemExit(f"Stage1 compiler installation is incomplete: {compiler_root}")
    try:
        pinned_stage0_revision = checked_in_stage0_revision(root)
        snapshot_std = Path(validated_stage1_snapshot_std_root(
            str(frontend_snapshot),
            str(stage1),
            str(compiler_root),
            str(compiler_root),
            pinned_frontend_revision,
            pinned_stage0_revision=pinned_stage0_revision,
            require_stage0_binding=True,
        ))
    except (OSError, ValueError) as error:
        raise SystemExit(f"pinned Stage1/compiler snapshot qualification failed: {error}") from error
    canonical_std = compiler_root / "elisacore_std"
    try:
        assert_canonical_std_matches_snapshot(snapshot_std, canonical_std)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    freshness = subprocess.run(
        ["bash", str(freshness_script), str(stage1)],
        capture_output=True,
        text=True,
        cwd=compiler_root,
        env=compiler_env,
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
        # Current Stage1 injects the canonical runtime modules for executable builds.
        # The source-binding fixture predates that behavior and explicitly included
        # the same modules, which now duplicates declarations from profiler hooks.
        harness = re.sub(
            r'^include "[^"\n]*/elisacore_std/(?:elisacore_runtime_prelude|collections|elisacore_runtime_strings)\.elisa"\n',
            "",
            harness,
            flags=re.MULTILINE,
        )
        harness = harness.replace(
            'include "../src/proof/replay.elisa"', _test_replay_includes(root, scratch)
        )
        harness = harness.replace(str(frontend_snapshot), str(frontend_snapshot.resolve()))

        with tempfile.TemporaryDirectory(prefix="bounded-counter-source-replay-", dir=root / "examples") as temporary:
            directory = Path(temporary)
            source_path = directory / "bounded_counter_source_replay.elisa"
            executable = directory / "bounded_counter_source_replay"
            canonical_std = canonical_std.resolve()
            harness = harness.replace(
                "../../Elisa-compiler/elisacore_std/", str(canonical_std) + "/"
            ).replace("../../Elisa-compiler/", str(frontend_snapshot.resolve()) + "/").replace(
                'include "../src/', 'include "../../src/'
            )
            harness = _grant_global_effects_to_harness_calls(harness)
            source_path.write_text(harness, encoding="utf-8")
            compiled = subprocess.run(
                [str(stage1_wrapper), "-emit", "exe", "-O0", "-o", str(executable), str(source_path)],
                capture_output=True,
                text=True,
                cwd=root,
                env=compiler_env,
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
