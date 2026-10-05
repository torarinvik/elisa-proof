"""Product object keys follow textual include dependencies, not every src file."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts/build_manifest.py"


def digest(snapshot: Path, main: str) -> str:
    result = subprocess.run(
        ["python3", str(MANIFEST), "--dependency-root", str(snapshot),
         "--dependency-main", main],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def identity(snapshot: Path, main: str, compiler: Path, clang: str, link_input: Path,
             output: Path, environment=None, recipe: Path = None) -> str:
    command = ["python3", str(MANIFEST), "--identity-only", "--identity-root", str(snapshot),
         "--identity-main", main, "--identity-object-key", "object-key",
         "--identity-compiler", str(compiler), "--identity-compiler-product", str(compiler),
         "--identity-clang", clang, "--identity-link-input", str(link_input),
         "--identity-link-flags=-dead_strip", "--identity-output", str(output)]
    if recipe is not None:
        command.extend(["--identity-recipe", str(recipe)])
    result = subprocess.run(command, check=True, capture_output=True, text=True, env=environment)
    return result.stdout.strip()


def env_digest(environment=None) -> str:
    result = subprocess.run(["python3", str(MANIFEST), "--effective-env-digest"],
                            check=True, capture_output=True, text=True, env=environment)
    return result.stdout.strip()


def recipes_digest(recipe: Path) -> str:
    result = subprocess.run(
        ["python3", str(MANIFEST), "--recipes-digest", "--recipe-path", str(recipe)],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def run_outside_closure_build_control(base: Path) -> None:
    """Exercise build.sh reuse decisions with an isolated fixture and deterministic tools."""
    project = base / "fixture"
    compiler = project / "compiler"
    proof = project / "proof"
    tools = project / "tools"
    for directory in (compiler / "src", compiler / "elisacore_std", compiler / "test/parity",
                      proof / "src", proof / "examples", proof / "scripts", tools):
        directory.mkdir(parents=True, exist_ok=True)

    for name in ("build.sh", "compiler_snapshot.sh", "compiler_provenance.sh", "link_flags.sh",
                 "build_manifest.py", "compiler_environment.py", "verify_product_pair.py"):
        shutil.copy2(ROOT / "scripts" / name, proof / "scripts" / name)
    (compiler / "src/front.elisa").write_text("frontend\n")
    (compiler / "elisacore_std/placeholder").write_text("fixture\n")
    (compiler / "test/parity/profile_hooks.c").write_text("void profile_hook(void) {}\n")
    subprocess.run(["git", "init", "-q", str(compiler)], check=True)
    subprocess.run(["git", "-C", str(compiler), "add", "."], check=True)
    subprocess.run(["git", "-C", str(compiler), "-c", "user.name=Build test",
                    "-c", "user.email=build-test@example.invalid", "commit", "-qm", "fixture"], check=True)
    revision = subprocess.run(["git", "-C", str(compiler), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    (proof / "ELISA_COMPILER_REV").write_text(revision + "\n")
    (proof / "src/main.elisa").write_text('include "./shared.elisa"\nmain\n')
    (proof / "src/replay_main.elisa").write_text("replay\n")
    (proof / "src/shared.elisa").write_text("shared\n")
    (proof / "src/unrelated.elisa").write_text("outside closure\n")
    (proof / "examples/verified.elisa").write_text("fixture\n")

    compiler_log = project / "compiler.log"
    clang_log = project / "clang.log"
    mock_compiler = tools / "mock-elisac"
    mock_compiler.write_text("""#!/usr/bin/env python3
import pathlib, sys
args = sys.argv[1:]
output = pathlib.Path(args[args.index('-o') + 1])
source = pathlib.Path(args[-1])
with open(__import__('os').environ['MOCK_COMPILER_LOG'], 'a') as log:
    log.write(source.name + '\\n')
gate = __import__('os').environ.get('MOCK_COMPILER_GATE_DIR')
if gate:
    gate = pathlib.Path(gate)
    (gate / 'entered').touch()
    while not (gate / 'release').exists():
        __import__('time').sleep(0.01)
output.write_bytes(('object:' + source.name).encode())
""")
    mock_clang = tools / "clang"
    mock_clang.write_text("""#!/usr/bin/env python3
import os, pathlib, sys
args = sys.argv[1:]
if args == ['--version']:
    print('fixture clang 1')
elif args == ['-dumpmachine']:
    print('x86_64-fixture-linux')
elif args == ['-print-resource-dir']:
    print('/fixture/clang/resources')
else:
    output = pathlib.Path(args[args.index('-o') + 1])
    if '-c' in args:
        with open(os.environ['MOCK_CLANG_LOG'], 'a') as log:
            log.write('hook\\n')
        output.write_bytes(b'hook-object')
    else:
        with open(os.environ['MOCK_CLANG_LOG'], 'a') as log:
            log.write('link\\n')
        if os.environ.get('MOCK_FAIL_REPLAY_LINK') == '1' and output.name.endswith('.1'):
            raise SystemExit(42)
        output.write_bytes(b'fixture-binary')
""")
    mock_uname = tools / "uname"
    mock_uname.write_text("""#!/bin/sh
if [ "$1" = "-smr" ]; then
    printf 'fixture-system fixture-machine %s\\n' "$MOCK_UNAME_RELEASE"
else
    exec /usr/bin/uname "$@"
fi
""")
    for executable in (mock_compiler, mock_clang, mock_uname):
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)

    environment = dict(os.environ, ELISA_COMPILER_BIN=str(mock_compiler),
                       ELISA_COMPILER_SRC=str(compiler), ELISA_COMPILER_REV=revision,
                       ELISA_CLANG=str(mock_clang), ELISA_PROOF_PRODUCTS="all",
                       ELISA_PROOF_OUTPUT=str(project / "compat-proof" / "elisa-proof"),
                       ELISA_PROOF_REPLAY_OUTPUT=str(project / "other-root" / "elisa-proof-replay"),
                       ELISA_PROOF_OBJECT_CACHE="0", MOCK_COMPILER_LOG=str(compiler_log),
                       MOCK_CLANG_LOG=str(clang_log), MOCK_UNAME_RELEASE="release-one",
                       PATH=str(tools) + os.pathsep + os.environ["PATH"])
    build = proof / "scripts/build.sh"
    initial = subprocess.run([str(build)], cwd=proof, env=environment,
                             capture_output=True, text=True)
    assert initial.returncode == 0, initial.stderr
    assert sorted(compiler_log.read_text().splitlines()) == ["main.elisa", "replay_main.elisa"], (compiler_log.read_text(), initial.stderr)
    assert clang_log.read_text().splitlines() == ["hook", "link", "link"], (clang_log.read_text(), initial.stderr)
    products = [Path(environment["ELISA_PROOF_OUTPUT"]),
                Path(environment["ELISA_PROOF_REPLAY_OUTPUT"])]
    generation_root = proof / "build/elisa-proof-generations"

    def resolve_generation(env=environment) -> dict:
        result = subprocess.run(
            ["python3", str(proof / "scripts/verify_product_pair.py"), "resolve",
             "--generation-root", str(generation_root)], env=env,
            check=True, capture_output=True, text=True,
        )
        resolved = json.loads(result.stdout)
        assert all(Path(row["binary"]).is_file() for row in resolved["products"].values())
        assert Path(resolved["products"]["elisa-proof"]["binary"]).parent == Path(
            resolved["products"]["elisa-proof-replay"]["binary"]).parent
        return resolved

    initial_generation = resolve_generation()
    assert initial_generation["pair_generation"]
    assert all(json.loads(Path(row["manifest"]).read_text())["pair_generation"] ==
               initial_generation["pair_generation"] for row in initial_generation["products"].values())

    current_pointer = generation_root / "CURRENT"
    pointer_value = current_pointer.read_text(encoding="ascii")
    current_pointer.write_text("../not-a-generation\n", encoding="ascii")
    refused_pointer = subprocess.run(
        ["python3", str(proof / "scripts/verify_product_pair.py"), "resolve",
         "--generation-root", str(generation_root)], capture_output=True, text=True,
    )
    current_pointer.write_text(pointer_value, encoding="ascii")
    assert refused_pointer.returncode == 2 and "valid generation identity" in refused_pointer.stderr

    def product_state() -> list:
        artifacts = [artifact for path in products for artifact in
                     (path, path.with_name(path.name + ".manifest.json"),
                      path.with_name(path.name + ".manifest.json.sha256"))]
        return [(artifact.read_bytes(), artifact.stat().st_mtime_ns) for artifact in artifacts]

    binaries_before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in products]
    manifest_proofs_before = [json.loads(path.with_name(path.name + ".manifest.json").read_text())["proof"]
                              for path in products]

    (proof / "src/unrelated.elisa").write_text("outside closure edited\n")
    after_edit = subprocess.run([str(build)], cwd=proof, env=environment,
                                capture_output=True, text=True)
    assert after_edit.returncode == 0, (after_edit.returncode, after_edit.stdout, after_edit.stderr)
    assert "product src/main.elisa is unchanged" in after_edit.stderr
    assert "product src/replay_main.elisa is unchanged" in after_edit.stderr
    assert sorted(compiler_log.read_text().splitlines()) == ["main.elisa", "replay_main.elisa"]
    assert clang_log.read_text().splitlines() == ["hook", "link", "link"]
    after = product_state()
    binaries_after = [(path.read_bytes(), path.stat().st_mtime_ns) for path in products]
    assert binaries_after == binaries_before, (initial.stderr, after_edit.stderr)
    current_tree = hashlib.sha256()
    for directory, subdirectories, files in os.walk(proof / "src"):
        subdirectories.sort()
        for name in sorted(files):
            path = Path(directory) / name
            current_tree.update(path.relative_to(proof / "src").as_posix().encode() + b"\0")
            current_tree.update(hashlib.sha256(path.read_bytes()).digest())
    manifest_proofs_after = [json.loads(path.with_name(path.name + ".manifest.json").read_text())["proof"]
                             for path in products]
    assert all(proof_info["source_tree_sha256"] == current_tree.hexdigest()
               for proof_info in manifest_proofs_after), manifest_proofs_after
    assert manifest_proofs_after[0] == manifest_proofs_after[1]
    assert manifest_proofs_after != manifest_proofs_before
    for path in products:
        manifest = path.with_name(path.name + ".manifest.json")
        sidecar = path.with_name(path.name + ".manifest.json.sha256")
        assert sidecar.read_text().strip() == hashlib.sha256(manifest.read_bytes()).hexdigest()

    assert sorted(compiler_log.read_text().splitlines()) == ["main.elisa", "replay_main.elisa"]
    assert clang_log.read_text().splitlines() == ["hook", "link", "link"]

    changed_kernel = dict(environment, MOCK_UNAME_RELEASE="release-two")
    after_kernel_change = subprocess.run([str(build)], cwd=proof, env=changed_kernel,
                                         check=True, capture_output=True, text=True)
    assert "product src/main.elisa is unchanged" in after_kernel_change.stderr
    assert "product src/replay_main.elisa is unchanged" in after_kernel_change.stderr
    assert sorted(compiler_log.read_text().splitlines()) == ["main.elisa", "replay_main.elisa"]
    assert clang_log.read_text().splitlines() == ["hook", "link", "link"]
    assert product_state() == after, (initial.stderr, after_kernel_change.stderr)

    # A damaged sidecar must invalidate only its product and drive the full build
    # path through compile, link, manifest write, and checksum refresh.
    main_checksum = products[0].with_name(products[0].name + ".manifest.json.sha256")
    main_checksum.write_text("0" * 64 + "\n", encoding="ascii")
    after_checksum_corruption = subprocess.run([str(build)], cwd=proof, env=environment,
                                                capture_output=True, text=True)
    assert after_checksum_corruption.returncode == 0, (after_checksum_corruption.returncode,
                                                        after_checksum_corruption.stdout,
                                                        after_checksum_corruption.stderr)
    assert "product src/main.elisa is unchanged" not in after_checksum_corruption.stderr
    assert "product src/replay_main.elisa is unchanged" in after_checksum_corruption.stderr
    assert sorted(compiler_log.read_text().splitlines()) == ["main.elisa", "main.elisa", "replay_main.elisa"]
    assert clang_log.read_text().splitlines() == ["hook", "link", "link", "link"]
    refreshed = main_checksum.read_text(encoding="ascii").strip()
    assert refreshed == hashlib.sha256(products[0].with_name(products[0].name + ".manifest.json").read_bytes()).hexdigest()

    # Hold a first build in its compile phase. A second build against the same
    # output tree must fail at the lock before either can publish products.
    (proof / "src/main.elisa").write_text('include "./shared.elisa"\nmain changed\n')
    (proof / "src/replay_main.elisa").write_text("replay changed\n")
    before_concurrent = product_state()
    gate = project / "compile-gate"
    gate.mkdir()
    gated_environment = dict(environment, MOCK_COMPILER_GATE_DIR=str(gate))
    first_build = subprocess.Popen([str(build)], cwd=proof, env=gated_environment,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 20
    while not (gate / "entered").exists() and time.monotonic() < deadline:
        if first_build.poll() is not None:
            stdout, stderr = first_build.communicate()
            raise AssertionError(f"first build exited before compile gate: {stdout} {stderr}")
        time.sleep(0.01)
    assert (gate / "entered").exists(), "first build did not reach compile gate"
    lock = proof / "build/.elisa-proof-build.lock"
    assert lock.is_dir()
    concurrent = subprocess.run([str(build)], cwd=proof, env=environment,
                                capture_output=True, text=True)
    assert concurrent.returncode == 2, (concurrent.returncode, concurrent.stdout, concurrent.stderr)
    assert "another proof build owns" in concurrent.stderr, concurrent.stderr
    assert product_state() == before_concurrent
    (gate / "release").touch()
    first_stdout, first_stderr = first_build.communicate(timeout=30)
    assert first_build.returncode == 0, (first_stdout, first_stderr)
    assert not lock.exists()
    concurrent_pair = [json.loads(path.with_name(path.name + ".manifest.json").read_text())
                       for path in products]
    assert concurrent_pair[0]["proof"] == concurrent_pair[1]["proof"]
    for path in products:
        manifest = path.with_name(path.name + ".manifest.json")
        sidecar = path.with_name(path.name + ".manifest.json.sha256")
        assert sidecar.read_text().strip() == hashlib.sha256(manifest.read_bytes()).hexdigest()

    # Failure on replay linking happens before either staged product is installed.
    # The previous coherent pair must remain byte-for-byte and timestamp-identical.
    old_pair = [json.loads(path.with_name(path.name + ".manifest.json").read_text())
                for path in products]
    before_failed_build = product_state()
    (proof / "src/main.elisa").write_text('include "./shared.elisa"\nmain failed-generation\n')
    (proof / "src/replay_main.elisa").write_text("replay failed-generation\n")
    failed_environment = dict(environment, MOCK_FAIL_REPLAY_LINK="1")
    failed = subprocess.run([str(build)], cwd=proof, env=failed_environment,
                            capture_output=True, text=True)
    assert failed.returncode == 42, (failed.returncode, failed.stdout, failed.stderr)
    assert not lock.exists()
    failed_pair = [json.loads(path.with_name(path.name + ".manifest.json").read_text())
                   for path in products]
    assert failed_pair == old_pair
    assert product_state() == before_failed_build

    # The immutable generation has already been published when compatibility files
    # are copied. Interrupt after the proof compatibility binary changes but before
    # replay changes: the legacy paths mismatch, while a pinned generation is sound.
    published_pair = [json.loads(path.with_name(path.name + ".manifest.json").read_text())
                      for path in products]
    before_publish_interrupt = product_state()
    (proof / "src/main.elisa").write_text('include "./shared.elisa"\nmain interrupted-generation\n')
    (proof / "src/replay_main.elisa").write_text("replay interrupted-generation\n")
    mock_mv = tools / "mv"
    mock_mv.write_text("""#!/usr/bin/env python3
import os, pathlib, sys
args = sys.argv[1:]
source, destination = pathlib.Path(args[-2]), pathlib.Path(args[-1])
if (os.environ.get('MOCK_INTERRUPT_BEFORE_REPLAY_PUBLISH') == '1'
        and destination.name == 'elisa-proof-replay'
        and source.name.startswith('elisa-proof.') and source.name.endswith('.1')):
    pathlib.Path(os.environ['MOCK_PUBLISH_FAILURE_MARKER']).touch()
    raise SystemExit(88)
os.execv('/bin/mv', ['mv', *args])
""")
    mock_mv.chmod(mock_mv.stat().st_mode | stat.S_IXUSR)
    publish_marker = project / "publish-interrupted"
    interrupted_environment = dict(environment, MOCK_INTERRUPT_BEFORE_REPLAY_PUBLISH="1",
                                   MOCK_PUBLISH_FAILURE_MARKER=str(publish_marker))
    interrupted = subprocess.run([str(build)], cwd=proof, env=interrupted_environment,
                                 capture_output=True, text=True)
    assert interrupted.returncode == 88, (interrupted.returncode, interrupted.stdout, interrupted.stderr)
    assert publish_marker.exists(), "injected interruption did not reach the second product rename"
    assert not lock.exists()
    interrupted_pair = [json.loads(path.with_name(path.name + ".manifest.json").read_text())
                        for path in products]
    assert interrupted_pair[0]["proof"]["source_tree_sha256"] != published_pair[0]["proof"]["source_tree_sha256"]
    assert interrupted_pair[1] == published_pair[1]
    assert interrupted_pair[0]["proof"]["source_tree_sha256"] != interrupted_pair[1]["proof"]["source_tree_sha256"]
    pinned_after_compat_interrupt = resolve_generation()
    assert pinned_after_compat_interrupt["pair_generation"] != initial_generation["pair_generation"]
    pinned_pair = [json.loads(Path(row["manifest"]).read_text())
                   for row in pinned_after_compat_interrupt["products"].values()]
    assert pinned_pair[0]["pair_generation"] == pinned_pair[1]["pair_generation"]
    assert pinned_pair[0]["proof"] == pinned_pair[1]["proof"]
    for path in products:
        manifest = path.with_name(path.name + ".manifest.json")
        sidecar = path.with_name(path.name + ".manifest.json.sha256")
        assert sidecar.read_text().strip() == hashlib.sha256(manifest.read_bytes()).hexdigest()
    partial_state = product_state()
    assert partial_state[:3] != before_publish_interrupt[:3]
    assert partial_state[3:] == before_publish_interrupt[3:]

    # A later ordinary build repairs the pair from the current source snapshot.
    repaired = subprocess.run([str(build)], cwd=proof, env=environment,
                              capture_output=True, text=True)
    assert repaired.returncode == 0, (repaired.returncode, repaired.stdout, repaired.stderr)
    repaired_pair = [json.loads(path.with_name(path.name + ".manifest.json").read_text())
                     for path in products]
    assert repaired_pair[0]["proof"] == repaired_pair[1]["proof"]
    resolve_generation()

    # Fail at every directory/pointer publication edge. Before CURRENT replacement
    # the previous generation remains selected; after replacement the new complete
    # generation is selected. Unreferenced completed generation directories are safe.
    failure_boundaries = {
        "before-generation-rename": False,
        "after-generation-rename": False,
        "before-pointer-replace": False,
        "after-pointer-replace": True,
    }
    for number, (boundary, selects_new) in enumerate(failure_boundaries.items()):
        before = resolve_generation()
        (proof / "src/main.elisa").write_text(f'include "./shared.elisa"\nmain boundary {number}\n')
        (proof / "src/replay_main.elisa").write_text(f"replay boundary {number}\n")
        failed_boundary_env = dict(environment, ELISA_PROOF_PUBLISH_FAIL_AT=boundary)
        stopped = subprocess.run([str(build)], cwd=proof, env=failed_boundary_env,
                                  capture_output=True, text=True)
        assert stopped.returncode == 2 and boundary in stopped.stderr, (boundary, stopped.returncode, stopped.stderr)
        after = resolve_generation()
        assert (after["pair_generation"] != before["pair_generation"]) == selects_new, (boundary, before, after)
        pair_manifests = [json.loads(Path(row["manifest"]).read_text())
                          for row in after["products"].values()]
        assert pair_manifests[0]["pair_generation"] == pair_manifests[1]["pair_generation"]
        assert pair_manifests[0]["proof"] == pair_manifests[1]["proof"]
    legacy_boundaries = (
        "legacy-proof-binary", "legacy-proof-manifest", "legacy-proof-checksum",
        "legacy-replay-binary", "legacy-replay-manifest", "legacy-replay-checksum",
    )
    for number, boundary in enumerate(legacy_boundaries):
        before = resolve_generation()
        (proof / "src/main.elisa").write_text(f'include "./shared.elisa"\nlegacy boundary {number}\n')
        (proof / "src/replay_main.elisa").write_text(f"legacy replay boundary {number}\n")
        stopped = subprocess.run(
            [str(build)], cwd=proof,
            env=dict(environment, ELISA_PROOF_PUBLISH_FAIL_AT=boundary),
            capture_output=True, text=True,
        )
        assert stopped.returncode == 88 and boundary in stopped.stderr, (boundary, stopped.returncode, stopped.stderr)
        after = resolve_generation()
        assert after["pair_generation"] != before["pair_generation"], (boundary, before, after)
        manifests = [json.loads(Path(row["manifest"]).read_text())
                     for row in after["products"].values()]
        assert manifests[0]["pair_generation"] == manifests[1]["pair_generation"]
        assert manifests[0]["proof"] == manifests[1]["proof"]
    print("build publication: link failure preserved pair; legacy interruption left pinned generation "
          "coherent; all four authoritative and six compatibility boundaries resolved complete; "
          "separate compatibility roots passed")
    print("build publication source trees: installed-proof="
          f"{interrupted_pair[0]['proof']['source_tree_sha256']}; installed-replay="
          f"{interrupted_pair[1]['proof']['source_tree_sha256']}")

    # The single-product build has no pair-generation arguments. Keep this path under
    # `set -u`: macOS's system Bash 3.2 errors when an empty array is expanded directly.
    single_output = project / "single-root" / "elisa-proof"
    single_environment = dict(environment, ELISA_PROOF_PRODUCTS="one",
                              ELISA_PROOF_OUTPUT=str(single_output))
    single_build = subprocess.run(["/bin/bash", str(build)], cwd=proof, env=single_environment,
                                  capture_output=True, text=True)
    assert single_build.returncode == 0, (single_build.stdout, single_build.stderr)
    assert "PAIR_MANIFEST_ARGS" not in single_build.stderr, single_build.stderr
    single_manifest_path = single_output.with_name(single_output.name + ".manifest.json")
    assert single_manifest_path.is_file(), (single_build.stdout, single_build.stderr)
    single_manifest = json.loads(single_manifest_path.read_text())
    assert single_manifest["pair_generation"] is None, single_manifest


with tempfile.TemporaryDirectory(prefix="elisa-build-closure-") as directory:
    base = Path(directory)
    proof = base / "elisa-proof"
    compiler = base / "Elisa-compiler"
    (proof / "src").mkdir(parents=True)
    (compiler / "src").mkdir(parents=True)
    (proof / "src/main.elisa").write_text('include "./shared.elisa"\nmain\n')
    (proof / "src/replay_main.elisa").write_text("replay\n")
    (proof / "src/shared.elisa").write_text('include "../../Elisa-compiler/src/front.elisa"\nshared\n')
    (proof / "src/unrelated.elisa").write_text("unrelated\n")
    (compiler / "src/front.elisa").write_text("frontend\n")

    main_before = digest(proof, "src/main.elisa")
    replay_before = digest(proof, "src/replay_main.elisa")
    (proof / "src/unrelated.elisa").write_text("unrelated edit\n")
    assert digest(proof, "src/main.elisa") == main_before
    assert digest(proof, "src/replay_main.elisa") == replay_before
    (compiler / "src/front.elisa").write_text("frontend edit\n")
    assert digest(proof, "src/main.elisa") != main_before
    assert digest(proof, "src/replay_main.elisa") == replay_before
    main_current = digest(proof, "src/main.elisa")
    replay_current = digest(proof, "src/replay_main.elisa")

    clang = shutil.which("clang")
    if clang:
        fake_compiler = base / "compiler.bin"
        fake_compiler.write_bytes(b"compiler")
        linked = base / "linked.o"
        linked.write_bytes(b"hooks")
        recipe = base / "build.sh"
        recipe.write_text("build recipe v1\n")
        first_recipe_digest = recipes_digest(recipe)
        output = base / "proof-bin"
        output.write_bytes(b"binary")
        main_output = base / "main-bin"
        main_output.write_bytes(b"binary")
        main_identity = identity(proof, "src/main.elisa", fake_compiler,
                                 clang, linked, main_output, recipe=recipe)
        proof_identity = identity(proof, "src/replay_main.elisa", fake_compiler,
                                  clang, linked, output, recipe=recipe)
        (proof / "src/unrelated.elisa").write_text("another unrelated edit\n")
        assert digest(proof, "src/main.elisa") == main_current
        assert digest(proof, "src/replay_main.elisa") == replay_current
        assert identity(proof, "src/main.elisa", fake_compiler,
                        clang, linked, main_output, recipe=recipe) == main_identity
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, recipe=recipe) == proof_identity
        build_jobs_env = dict(os.environ, ELISA_PROOF_BUILD_JOBS="9")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, build_jobs_env, recipe) == proof_identity
        unrelated_env = dict(os.environ, CODEX_THREAD_ID="different-session", TERM="vt100")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, unrelated_env, recipe) == proof_identity
        relevant_env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET="12.0")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, relevant_env, recipe) != proof_identity
        target_env = dict(os.environ, ELISA_TARGET_TRIPLE="aarch64-unknown-test")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, target_env, recipe) != proof_identity
        path_env = dict(os.environ, PATH="/p03-other-tools:" + os.environ.get("PATH", ""))
        sdk_env = dict(os.environ, SDKROOT="")
        assert env_digest(build_jobs_env) == env_digest(unrelated_env)
        assert env_digest(unrelated_env) != env_digest(relevant_env)
        assert env_digest(unrelated_env) != env_digest(target_env)
        assert env_digest(unrelated_env) != env_digest(path_env)
        assert env_digest(unrelated_env) != env_digest(sdk_env)
        linked.write_bytes(b"changed hooks")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, recipe=recipe) != proof_identity
        recipe.write_text("build recipe v2\n")
        assert recipes_digest(recipe) != first_recipe_digest
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, recipe=recipe) != proof_identity

        manifest = base / "proof-bin.manifest.json"
        manifest.write_text(json.dumps({"build_identity": proof_identity,
                                        "binary": {"sha256": hashlib.sha256(output.read_bytes()).hexdigest()}}))
        manifest_hash = base / "proof-bin.manifest.json.sha256"
        manifest_hash.write_text(hashlib.sha256(manifest.read_bytes()).hexdigest())
        check = ["python3", str(MANIFEST), "--check-existing", "--recorded-build-identity",
                 proof_identity, "--existing-binary", str(output), "--existing-manifest", str(manifest),
                 "--existing-manifest-sha256", str(manifest_hash)]
        assert subprocess.run(check).returncode == 0
        output.write_bytes(b"tampered binary")
        assert subprocess.run(check).returncode == 1
    run_outside_closure_build_control(base / "orchestration")
print("build dependency closure: unrelated edits preserve both end-to-end products; transitive includes invalidate")
