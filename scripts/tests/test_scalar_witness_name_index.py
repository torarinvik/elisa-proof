"""Differentially exercise the scalar-witness name index with a fresh Stage1 compiler."""

import hashlib
from pathlib import Path
import os
import platform
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
PROOF_SOURCE_ROOT = Path(os.environ.get("ELISA_PROOF_SOURCE_ROOT", ROOT))
COMPILER_ROOT = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler"))
STAGE1 = COMPILER_ROOT / "bin" / "elisac-stage1"
FRESHNESS_CHECK = COMPILER_ROOT / "scripts" / "assert_stage1_fresh.sh"
FIXTURE = ROOT / "test" / "repro" / "scalar_witness_name_index.elisa"


def fnv1a_u32(text: str) -> int:
    value = 2166136261
    for byte in text.encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


def compiler_source_revision() -> str:
    snapshot = COMPILER_ROOT / "SNAPSHOT"
    if snapshot.is_file():
        for line in snapshot.read_text(encoding="utf-8").splitlines():
            if line.startswith("source_revision:"):
                return line.split(":", 1)[1].strip()
        raise SystemExit(f"compiler snapshot has no source_revision: {snapshot}")

    # A fresh source checkout is a valid compiler root too. Require it to be clean so the
    # reported revision actually identifies the frontend checked by assert_stage1_fresh.sh.
    revision = subprocess.run(
        ["git", "-C", str(COMPILER_ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "-C", str(COMPILER_ROOT), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if dirty:
        raise SystemExit(f"compiler checkout is dirty; refusing to claim revision {revision}")
    return revision


def run(*command: str, cwd: Path = ROOT, env: dict | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True, env=env)


def stage1_host_environment() -> dict:
    """Stage1 reads its host from these flags, which its wrapper normally exports; without
    them a raw Stage1 call on Linux compiles the macOS mmap flags and the product aborts."""
    env = dict(os.environ)
    if platform.system() == "Linux":
        env.setdefault("ELISA_HOST_LINUX", "1")
        if platform.machine() in ("x86_64", "AMD64"):
            env.setdefault("ELISA_HOST_X86_64", "1")
    return env


# Apple ld spells dead stripping -dead_strip; GNU ld needs the flags scripts/link_flags.sh uses.
DEAD_STRIP_LINK = (["-Wl,-dead_strip"] if platform.system() == "Darwin"
                   else ["-no-pie", "-Wl,--gc-sections", "-Wl,--no-as-needed", "-lm"])


def materialize_fixture(destination: Path) -> None:
    """Point includes at the exact project/compiler roots being tested."""
    source = FIXTURE.read_text(encoding="utf-8")

    def absolute_include(match: re.Match[str]) -> str:
        relative = match.group(1)
        compiler_prefix = "../../../Elisa-compiler/"
        if relative.startswith(compiler_prefix):
            path = COMPILER_ROOT / relative[len(compiler_prefix):]
        elif relative.startswith("../../src/"):
            path = PROOF_SOURCE_ROOT / "src" / relative[len("../../src/"):]
        else:
            path = (FIXTURE.parent / relative).resolve()
        return f'include "{path}"'

    source = re.sub(r'^include "([^"]+)"$', absolute_include, source, flags=re.MULTILINE)

    # The production table stores the first compact-name ordinal in an occupied slot. Compare
    # that selected witness (or the refusal sentinel) to a direct source-order scan, rather than
    # merely checking that two test strings happen to collide.
    helpers = r'''extend ElisaProof:
    public:
        def test_make_unsigned_marker_width(name: sview, width: i64, position: Ast::Pos) -> Ast::Expr:
            return Ast::Expr.Call(Ast::Expr.Ident("__elisa_unsigned_type_bound", position), [Ast::Expr.Ident(name, position), Ast::Expr.IntLit(width, position)], [], position)

        def test_linear_first_name_index(facts: darray[Ast::Expr]&, name: sview) -> usize:
            ordinal: mutable usize = 0
            for fact in facts |ordinal, name|:
                scalar_name: sview = proof_scalar_marker_name(fact)
                unsigned_name: sview = proof_unsigned_marker_name(fact)
                if scalar_name != "":
                    return ordinal if scalar_name == name
                    ordinal <- ordinal + 1
                if unsigned_name != "":
                    return ordinal if unsigned_name == name
                    ordinal <- ordinal + 1
            return ordinal

        def test_index_first_name_index(witnesses: ProofScalarWitnesses&, name: sview) -> usize:
            capacity: usize = witnesses.name_slots.count
            return witnesses.names.count if name == "" or capacity == 0
            wanted_hash: u32 = proof_name_hash(name)
            slot: mutable usize = (wanted_hash.i64() % capacity.i64()).usize()
            probes: mutable usize = 0
            while probes < capacity |probes, slot, wanted_hash, name, witnesses, capacity|:
                ordinal: usize = witnesses.name_slots[slot]
                return witnesses.names.count if ordinal >= witnesses.names.count
                return ordinal if witnesses.name_hashes[ordinal] == wanted_hash and witnesses.names[ordinal] == name
                slot <- (slot + 1) % capacity
                probes <- probes + 1
            return witnesses.names.count

        def test_scalar_name_choice_parity(facts: darray[Ast::Expr]&, queries: darray[sview]&) -> bool:
            witnesses: ProofScalarWitnesses = proof_scalar_witness_markers(facts)
            for name in queries |name, witnesses, facts|:
                return false if test_index_first_name_index(witnesses, name) != test_linear_first_name_index(facts, name)
            return true
'''
    main_marker = "def main() -> i64 can[Memory.Allocate, Abort.Panic]:\n"
    if source.count(main_marker) != 1:
        raise SystemExit("R-019 fixture main anchor changed; refusing to run a partial regression")
    source = source.replace(main_marker, helpers + "\n" + main_marker, 1)
    anchor = '    return 9 if shadowed_markers.names[0] != shadowed_markers.names[2]\n'
    mixed_case = r'''

    # Interleave equal-full-hash names with multiple marker kinds, widths, duplicates, and
    # same-spelling declarations at separate source positions. Invalid/non-name markers must
    # remain refusals, and duplicates must select the first source-order witness.
    mixed_facts: mutable darray[Ast::Expr] = [
        test_make_scalar_marker(collision_a, Ast::pos_at_line(30)),
        test_make_unsigned_marker(collision_b, Ast::pos_at_line(31)),
        test_make_scalar_marker("shadowed", Ast::pos_at_line(32)),
        test_make_unsigned_marker_width("shadowed", 16, Ast::pos_at_line(33)),
        proof_signed_type_marker(Ast::Expr.Ident("signed_only", position), 16, position),
        proof_scalar_element_marker(Ast::Expr.Ident("element_only", position), 1, position, 8),
        test_make_unsigned_marker_width("shadowed", 8, Ast::pos_at_line(34)),
        Ast::Expr.Call(Ast::Expr.Ident("__elisa_unsigned_type_bound", position), [Ast::Expr.Ident("bad_width", position), Ast::Expr.IntLit(0, position)], [], position)
    ]
    mixed_queries: darray[sview] = [collision_a, collision_b, "shadowed", "signed_only", "element_only", "bad_width", "absent", ""]
    return 10 if not test_scalar_name_choice_parity(mixed_facts, mixed_queries)
    mixed_markers: ProofScalarWitnesses = proof_scalar_witness_markers(mixed_facts)
    return 11 if mixed_markers.names.count != 5
    linear_collision_choice: usize = test_linear_first_name_index(mixed_facts, collision_b)
    return 12 if linear_collision_choice == mixed_markers.names.count
    return 13 if test_index_first_name_index(mixed_markers, collision_b) != linear_collision_choice
    return 14 if proof_unsigned_marker_width_for_name(mixed_facts, "shadowed") != 8
    return 15 if proof_unsigned_marker_width_for_name(mixed_facts, collision_b) != 8
'''
    if source.count(anchor) != 1:
        raise SystemExit("R-019 fixture shadowing anchor changed; refusing to run a partial regression")
    source = source.replace(anchor, anchor + mixed_case, 1)
    destination.write_text(source, encoding="utf-8")


def main() -> None:
    if fnv1a_u32("r019-s6WXBpYWBJfn") != fnv1a_u32("r019-u22pK2GiCukM"):
        raise SystemExit("R-019 collision fixture no longer contains an exact FNV-1a collision")
    if not STAGE1.is_file() or not FRESHNESS_CHECK.is_file():
        raise SystemExit(f"fresh Stage1 compiler unavailable under {COMPILER_ROOT}")
    production_index = ROOT / "src" / "proof" / "linear" / "scalar_witness_index.elisa"
    selected_index = PROOF_SOURCE_ROOT / "src" / "proof" / "linear" / "scalar_witness_index.elisa"
    production_index_digest = hashlib.sha256(production_index.read_bytes()).hexdigest()
    selected_index_digest = hashlib.sha256(selected_index.read_bytes()).hexdigest()
    if selected_index_digest != production_index_digest:
        raise SystemExit("selected proof source root has a different scalar-witness index")

    # Fail closed on a stale binary; a locally available but unmatched Stage1 is not evidence.
    run(str(FRESHNESS_CHECK), str(STAGE1), cwd=COMPILER_ROOT)

    runtime = COMPILER_ROOT / "build" / "runtime" / "elisacore_runtime.o"
    hooks_source = COMPILER_ROOT / "test" / "parity" / "profile_hooks.c"
    if not hooks_source.is_file():
        # Installed snapshots intentionally carry the runtime/compiler sources, not the
        # compiler repository's test-only weak stubs. Use those stubs from the adjacent source
        # checkout only; they satisfy the optional profiling ABI and do not participate in
        # compilation or proof checking.
        hooks_source = ROOT.parent / "Elisa-compiler" / "test" / "parity" / "profile_hooks.c"
    clang = os.environ.get("CLANG", "clang")
    if not runtime.is_file() or not hooks_source.is_file():
        raise SystemExit("matching Stage1 runtime or profiler-hook source is unavailable")

    with tempfile.TemporaryDirectory(prefix="elisa-r019-stage1-") as temp:
        scratch = Path(temp)
        fixture = scratch / "scalar_witness_name_index.elisa"
        materialize_fixture(fixture)
        object_file = scratch / "scalar-witness-index.o"
        hooks_object = scratch / "profile-hooks.o"
        executable = scratch / "scalar-witness-index"
        run(str(STAGE1), "-permissive", "-emit", "obj", "-O0", "-o", str(object_file), str(fixture),
            env=stage1_host_environment())
        run(clang, "-c", str(hooks_source), "-o", str(hooks_object))
        run(clang, *DEAD_STRIP_LINK, "-o", str(executable), str(object_file), str(hooks_object),
            str(runtime))
        run(str(executable))

    source_revision = compiler_source_revision()
    runtime_digest = hashlib.sha256(runtime.read_bytes()).hexdigest()
    hooks_digest = hashlib.sha256(hooks_source.read_bytes()).hexdigest()
    print(f"R-019 Stage1 indexed-vs-linear oracle passed: revision={source_revision} runtime_sha256={runtime_digest} profiler_stub_sha256={hooks_digest}")
    print(f"proof_source_root={PROOF_SOURCE_ROOT} scalar_witness_index_sha256={production_index_digest}")
    print("Compared selected witness ordinal/refusal across full-hash collision, marker kinds, widths, duplicates, and shadowing")


if __name__ == "__main__":
    main()
