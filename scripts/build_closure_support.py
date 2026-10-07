"""Helpers for test_build_dependency_closure.py: product identity digests and the
outside-closure build-control fixture (split out to keep each file under 600 lines)."""
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
                 "build_manifest.py", "compiler_environment.py", "verify_product_pair.py",
                 "runtime_inputs.sh", "compiler_recipe_inputs.py"):
        shutil.copy2(ROOT / "scripts" / name, proof / "scripts" / name)
    # Add a fixture-only barrier in the copied publisher. This lets the test kill the
    # complete build process group at a real publication boundary without adding a
    # pause hook to the production publisher.
    fixture_publisher = proof / "scripts/verify_product_pair.py"
    publisher_source = fixture_publisher.read_text()
    publisher_source = publisher_source.replace(
        'def failpoint(name: str) -> None:\n',
        'def failpoint(name: str) -> None:\n'
        '    if os.environ.get("MOCK_PUBLISH_PAUSE_AT") == name:\n'
        '        Path(os.environ["MOCK_PUBLISH_PAUSE_MARKER"]).write_text(str(os.getpid()))\n'
        '        while Path(os.environ["MOCK_PUBLISH_PAUSE_RELEASE"]).exists():\n'
        '            import time\n'
        '            time.sleep(0.01)\n'
    )
    fixture_publisher.write_text(publisher_source)
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

    refreshed_generation = resolve_generation()
    assert refreshed_generation["pair_generation"] != initial_generation["pair_generation"]
    refreshed_pair = [json.loads(Path(row["manifest"]).read_text())
                      for row in refreshed_generation["products"].values()]
    assert refreshed_pair[0]["proof"] == manifest_proofs_after[0]
    assert refreshed_pair[1]["proof"] == manifest_proofs_after[1]
    assert all(pair_manifest["binary"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
               for pair_manifest, path in zip(refreshed_pair, products))

    # A second no-op with the same whole-source snapshot must preserve the new generation as
    # well as both executable and manifest bytes; provenance-only republishing is one-time.
    after_unrelated_edit = product_state()
    no_op_generation = refreshed_generation["pair_generation"]
    repeated_no_op = subprocess.run([str(build)], cwd=proof, env=environment,
                                    capture_output=True, text=True)
    assert repeated_no_op.returncode == 0, (repeated_no_op.stdout, repeated_no_op.stderr)
    assert product_state() == after_unrelated_edit
    assert resolve_generation()["pair_generation"] == no_op_generation

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

    # A missing manifest is not a cache hit: only the affected replay product
    # must be rebuilt while the proof product remains byte- and timestamp-stable.
    replay_manifest = products[1].with_name(products[1].name + ".manifest.json")
    replay_manifest.unlink()
    before_missing_manifest = compiler_log.read_text().splitlines()
    before_missing_link = clang_log.read_text().splitlines()
    proof_before_missing_manifest = (products[0].read_bytes(), products[0].stat().st_mtime_ns)
    missing_manifest_build = subprocess.run([str(build)], cwd=proof, env=environment,
                                            capture_output=True, text=True)
    assert missing_manifest_build.returncode == 0, (missing_manifest_build.stdout,
                                                     missing_manifest_build.stderr)
    assert compiler_log.read_text().splitlines() == before_missing_manifest + ["replay_main.elisa"]
    assert clang_log.read_text().splitlines() == before_missing_link + ["link"]
    assert (products[0].read_bytes(), products[0].stat().st_mtime_ns) == proof_before_missing_manifest

    # The products have independent source closures: editing a transitive proof
    # include rebuilds only the proof binary, and editing replay_main rebuilds
    # only replay. This verifies orchestration decisions, not just digest values.
    before_proof_closure_edit = compiler_log.read_text().splitlines()
    before_proof_closure_link = clang_log.read_text().splitlines()
    replay_before_proof_closure = (products[1].read_bytes(), products[1].stat().st_mtime_ns)
    (proof / "src/shared.elisa").write_text("shared changed inside proof closure\n")
    proof_closure_build = subprocess.run([str(build)], cwd=proof, env=environment,
                                         capture_output=True, text=True)
    assert proof_closure_build.returncode == 0, (proof_closure_build.stdout,
                                                  proof_closure_build.stderr)
    assert compiler_log.read_text().splitlines() == before_proof_closure_edit + ["main.elisa"]
    assert clang_log.read_text().splitlines() == before_proof_closure_link + ["link"]
    assert (products[1].read_bytes(), products[1].stat().st_mtime_ns) == replay_before_proof_closure

    before_replay_closure_edit = compiler_log.read_text().splitlines()
    before_replay_closure_link = clang_log.read_text().splitlines()
    proof_before_replay_closure = (products[0].read_bytes(), products[0].stat().st_mtime_ns)
    (proof / "src/replay_main.elisa").write_text("replay closure edit\n")
    replay_closure_build = subprocess.run([str(build)], cwd=proof, env=environment,
                                          capture_output=True, text=True)
    assert replay_closure_build.returncode == 0, (replay_closure_build.stdout,
                                                   replay_closure_build.stderr)
    assert compiler_log.read_text().splitlines() == before_replay_closure_edit + ["replay_main.elisa"]
    assert clang_log.read_text().splitlines() == before_replay_closure_link + ["link"]
    assert (products[0].read_bytes(), products[0].stat().st_mtime_ns) == proof_before_replay_closure

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

    # Kill a complete build process group after its immutable generation directory
    # is durable but before CURRENT switches. The resolver must select the old pair.
    # SIGKILL bypasses build.sh's EXIT cleanup, so recover the stale lock explicitly
    # after confirming its recorded owner is dead.
    before_kill = resolve_generation()
    (proof / "src/main.elisa").write_text('include "./shared.elisa"\nmain killed publication\n')
    (proof / "src/replay_main.elisa").write_text("replay killed publication\n")
    pause_marker = project / "publisher-paused.pid"
    pause_release = project / "publisher-release"
    pause_release.touch()
    kill_env = dict(environment, MOCK_PUBLISH_PAUSE_AT="before-pointer-replace",
                    MOCK_PUBLISH_PAUSE_MARKER=str(pause_marker),
                    MOCK_PUBLISH_PAUSE_RELEASE=str(pause_release))
    killed_build = subprocess.Popen([str(build)], cwd=proof, env=kill_env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    start_new_session=True)
    deadline = time.monotonic() + 30
    while not pause_marker.exists() and time.monotonic() < deadline:
        if killed_build.poll() is not None:
            stdout, stderr = killed_build.communicate()
            raise AssertionError(f"build exited before authoritative boundary: {stdout} {stderr}")
        time.sleep(0.01)
    assert pause_marker.exists(), "build did not reach the deterministic publisher barrier"
    publisher_pid = int(pause_marker.read_text())
    lock = proof / "build/.elisa-proof-build.lock"
    lock_owner = int((lock / "pid").read_text())
    assert lock_owner == killed_build.pid
    os.killpg(killed_build.pid, __import__("signal").SIGKILL)
    killed_stdout, killed_stderr = killed_build.communicate(timeout=10)
    assert killed_build.returncode == -__import__("signal").SIGKILL, (killed_build.returncode,
                                                                         killed_stdout, killed_stderr)
    # The shell owner has been reaped; the publisher PID is retained in the marker
    # only as evidence that SIGKILL targeted the blocked publisher process group.
    assert publisher_pid > 0
    assert lock.is_dir() and (lock / "pid").read_text().strip() == str(lock_owner)
    after_kill = resolve_generation()
    assert after_kill["pair_generation"] == before_kill["pair_generation"]
    # Owner death is confirmed by Popen completion; remove only this fixture lock.
    shutil.rmtree(lock)
    pause_release.unlink()

    restarted = subprocess.run([str(build)], cwd=proof, env=environment,
                               capture_output=True, text=True)
    assert restarted.returncode == 0, (restarted.returncode, restarted.stdout, restarted.stderr)
    after_restart = resolve_generation()
    assert after_restart["pair_generation"] != before_kill["pair_generation"]
    restart_manifests = [json.loads(Path(row["manifest"]).read_text())
                         for row in after_restart["products"].values()]
    assert restart_manifests[0]["pair_generation"] == restart_manifests[1]["pair_generation"]
    assert restart_manifests[0]["proof"] == restart_manifests[1]["proof"]
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
          "SIGKILL before CURRENT kept the old pair resolvable and restart published a complete pair; "
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

    # The single-product path does not invoke the pair publisher. Changing that
    # unrelated implementation must therefore preserve a true product no-op.
    # This catches recipe over-invalidation, not merely object-cache reuse: both
    # compiler and linker logs, binary bytes and product timestamp stay fixed.
    pair_publisher = proof / "scripts/verify_product_pair.py"
    pair_publisher.write_text(pair_publisher.read_text() + "\n# irrelevant to single-product builds\n")
    single_compile_before = compiler_log.read_text().splitlines()
    single_link_before = clang_log.read_text().splitlines()
    single_binary_before = (single_output.read_bytes(), single_output.stat().st_mtime_ns)
    single_noop = subprocess.run([str(build)], cwd=proof, env=single_environment,
                                 capture_output=True, text=True)
    assert single_noop.returncode == 0, (single_noop.stdout, single_noop.stderr)
    assert "product src/main.elisa is unchanged" in single_noop.stderr, single_noop.stderr
    assert compiler_log.read_text().splitlines() == single_compile_before
    assert clang_log.read_text().splitlines() == single_link_before
    assert (single_output.read_bytes(), single_output.stat().st_mtime_ns) == single_binary_before

    # The same recipe is relevant in pair mode, where the publisher is invoked.
    # Ensure the single-mode optimization did not erase that dependency.
    all_compile_before = compiler_log.read_text().splitlines()
    all_link_before = clang_log.read_text().splitlines()
    all_rebuild = subprocess.run([str(build)], cwd=proof, env=environment,
                                 capture_output=True, text=True)
    assert all_rebuild.returncode == 0, (all_rebuild.stdout, all_rebuild.stderr)
    all_compile_after = compiler_log.read_text().splitlines()
    assert all_compile_after[:len(all_compile_before)] == all_compile_before
    assert sorted(all_compile_after[len(all_compile_before):]) == ["main.elisa", "replay_main.elisa"]
    assert clang_log.read_text().splitlines() == all_link_before + ["link", "link"]
