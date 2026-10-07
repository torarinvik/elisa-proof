"""Build snapshots and toolchain identities remain stable through publication."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPTS = (
    "build.sh", "compiler_snapshot.sh", "compiler_provenance.sh", "link_flags.sh",
    "build_manifest.py", "compiler_environment.py", "verify_product_pair.py",
    "runtime_inputs.sh", "compiler_recipe_inputs.py",
)


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for directory, subdirectories, files in os.walk(root):
        subdirectories.sort()
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def executable(path: Path, contents: str) -> None:
    path.write_text(contents)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def commit_fixture(root: Path, message: str) -> str:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Build test",
         "-c", "user.email=build-test@example.invalid", "commit", "-qm", message],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="elisa-build-snapshot-race-") as directory:
        base = Path(directory)
        proof = base / "elisa-proof"
        compiler_source = base / "Elisa-compiler"
        tools = base / "tools"
        for path in (proof / "scripts", proof / "src", proof / "examples",
                     compiler_source / "src", compiler_source / "elisacore_std",
                     compiler_source / "test/parity", tools):
            path.mkdir(parents=True, exist_ok=True)
        for name in BUILD_SCRIPTS:
            shutil.copy2(ROOT / "scripts" / name, proof / "scripts" / name)

        # Pause after the src subtree has been copied, while the overall snapshot
        # preparation is still running and before examples are copied.
        snapshot_script = proof / "scripts/compiler_snapshot.sh"
        snapshot_source = snapshot_script.read_text()
        source_copy = 'rsync -ac --delete "$SNAPSHOT_ROOT_DIR/src/" "$SNAPSHOT_ROOT/src/"\n'
        assert snapshot_source.count(source_copy) == 1, "expected one proof src copy boundary"
        snapshot_source = snapshot_source.replace(
            source_copy,
            source_copy
            + 'if [[ -n "${MOCK_SNAPSHOT_READY:-}" ]]; then\n'
            + '    printf "ready\\n" > "$MOCK_SNAPSHOT_READY"\n'
            + '    while [[ ! -f "$MOCK_SNAPSHOT_RELEASE" ]]; do sleep 0.01; done\n'
            + 'fi\n',
        )
        assert snapshot_source != snapshot_script.read_text(), "snapshot barrier insertion point changed"
        snapshot_script.write_text(snapshot_source)

        (compiler_source / "src/front.elisa").write_text("mock frontend v1\n")
        (compiler_source / "elisacore_std/placeholder").write_text("mock stdlib\n")
        (compiler_source / "test/parity/profile_hooks.c").write_text("void profile_hook(void) {}\n")
        compiler_revision = commit_fixture(compiler_source, "mock compiler fixture")

        (proof / "src/main.elisa").write_text('include "./shared.elisa"\nmain\n')
        (proof / "src/replay_main.elisa").write_text('include "./shared.elisa"\nreplay\n')
        (proof / "src/shared.elisa").write_text("snapshot sentinel v1\n")
        (proof / "examples/fixture.elisa").write_text("example v1\n")
        proof_revision = commit_fixture(proof, "proof fixture baseline")

        executable(tools / "mock-elisac", """#!/usr/bin/env python3
import hashlib, json, os, pathlib, sys
args = sys.argv[1:]
output = pathlib.Path(args[args.index('-o') + 1])
source = pathlib.Path(args[-1])
mutation_marker = os.environ.get('MOCK_COMPILER_MUTATION_MARKER')
if os.environ.get('MOCK_MUTATE_COMPILER_DURING_COMPILE') and mutation_marker:
    marker = pathlib.Path(mutation_marker)
    if not marker.exists():
        compiler_script = pathlib.Path(__file__)
        compiler_script.write_text(compiler_script.read_text() + '\\n# changed during a compile\\n')
        marker.touch()
src_root = source.parent
digest = hashlib.sha256()
for directory, subdirectories, files in os.walk(src_root):
    subdirectories.sort()
    for name in sorted(files):
        path = pathlib.Path(directory) / name
        digest.update(path.relative_to(src_root).as_posix().encode() + b'\\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
record = {
    'compiled_source_tree_sha256': digest.hexdigest(),
    'entry': source.name,
    'sentinel': (src_root / 'shared.elisa').read_text(),
}
output.write_text(json.dumps(record, sort_keys=True))
""")
        executable(tools / "clang", """#!/usr/bin/env python3
import json, pathlib, sys
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
        output.write_bytes(b'mock profiler hooks')
    else:
        objects = []
        for value in args:
            path = pathlib.Path(value)
            if path.is_file() and path.suffix == '.o':
                try:
                    objects.append(json.loads(path.read_text()))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
        output.write_text(json.dumps({'compiled_objects': objects}, sort_keys=True))
""")
        executable(tools / "uname", """#!/bin/sh
if [ "$1" = "-smr" ]; then
    printf 'fixture-system fixture-machine test-release\\n'
else
    printf 'fixture-system\\n'
fi
""")

        ready = base / "snapshot-ready"
        release = base / "snapshot-release"
        environment = dict(
            os.environ,
            ELISA_COMPILER_BIN=str(tools / "mock-elisac"),
            ELISA_COMPILER_SRC=str(compiler_source),
            ELISA_COMPILER_REV=compiler_revision,
            ELISA_CLANG=str(tools / "clang"),
            ELISA_PROOF_PRODUCTS="all",
            ELISA_PROOF_OBJECT_CACHE="0",
            MOCK_SNAPSHOT_READY=str(ready),
            MOCK_SNAPSHOT_RELEASE=str(release),
            PATH=str(tools) + os.pathsep + os.environ["PATH"],
        )
        process = subprocess.Popen(
            [str(proof / "scripts/build.sh")], cwd=proof, env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            deadline = time.monotonic() + 30
            while not ready.exists() and time.monotonic() < deadline:
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    raise AssertionError(f"build exited before snapshot barrier: {stdout}\n{stderr}")
                time.sleep(0.01)
            assert ready.exists(), "build did not pause after copying src"

            snapshot_src = proof / "build/snapshot/elisa-proof/src"
            captured_digest = tree_digest(snapshot_src)
            assert (snapshot_src / "shared.elisa").read_text() == "snapshot sentinel v1\n"
            assert not (snapshot_src / "after_snapshot.elisa").exists()

            # Mutate both an already copied source and add another source while
            # preparation is paused. Neither may leak into the compiler's snapshot.
            (proof / "src/shared.elisa").write_text("live source sentinel v2\n")
            (proof / "src/after_snapshot.elisa").write_text("live new source v2\n")
            live_digest = tree_digest(proof / "src")
            assert live_digest != captured_digest
            assert tree_digest(snapshot_src) == captured_digest

            lock = proof / "build/.elisa-proof-build.lock"
            assert lock.is_dir()
            assert (lock / "pid").read_text().strip() == str(process.pid)
        finally:
            release.touch()
            if process.poll() is None:
                process.communicate(timeout=90)

        stdout, stderr = process.communicate()
        assert process.returncode == 0, (process.returncode, stdout, stderr)
        assert not (proof / "build/.elisa-proof-build.lock").exists()

        resolved = subprocess.run(
            ["python3", str(proof / "scripts/verify_product_pair.py"), "resolve",
             "--generation-root", str(proof / "build/elisa-proof-generations")],
            check=True, capture_output=True, text=True,
        )
        pair = json.loads(resolved.stdout)
        products = pair["products"]
        assert set(products) == {"elisa-proof", "elisa-proof-replay"}
        manifests = [json.loads(Path(products[name]["manifest"]).read_text())
                     for name in ("elisa-proof", "elisa-proof-replay")]
        assert all(manifest["proof"]["head"] == proof_revision for manifest in manifests)
        assert all(manifest["proof"]["source_dirty"] for manifest in manifests)
        assert all(manifest["proof"]["source_tree_sha256"] == captured_digest
                   for manifest in manifests)
        assert manifests[0]["proof"] == manifests[1]["proof"]

        for product in products.values():
            executable_payload = json.loads(Path(product["binary"]).read_text())
            compiled = executable_payload["compiled_objects"]
            assert len(compiled) == 1
            assert compiled[0]["compiled_source_tree_sha256"] == captured_digest
            assert compiled[0]["sentinel"] == "snapshot sentinel v1\n"
            assert compiled[0]["sentinel"] != (proof / "src/shared.elisa").read_text()

        assert live_digest != manifests[0]["proof"]["source_tree_sha256"]

        # A compiler executable replaced while it is compiling must not publish an
        # object-cache entry, compatibility output, or a new authoritative pair.
        current_generation = (proof / "build/elisa-proof-generations/CURRENT").read_text()
        generations_before = {
            path.name for path in (proof / "build/elisa-proof-generations").iterdir()
            if path.is_dir()
        }
        race_outputs = proof / "build/toolchain-race"
        object_cache = base / "object-cache"
        mutation_marker = base / "compiler-mutated"
        race_environment = dict(
            environment,
            ELISA_PROOF_OUTPUT=str(race_outputs / "elisa-proof"),
            ELISA_PROOF_REPLAY_OUTPUT=str(race_outputs / "elisa-proof-replay"),
            ELISA_PROOF_OBJECT_CACHE=str(object_cache),
            ELISA_PROOF_BUILD_JOBS="1",
            MOCK_MUTATE_COMPILER_DURING_COMPILE="1",
            MOCK_COMPILER_MUTATION_MARKER=str(mutation_marker),
        )
        race = subprocess.run(
            [str(proof / "scripts/build.sh")], cwd=proof, env=race_environment,
            capture_output=True, text=True, timeout=90,
        )
        assert race.returncode == 2, (race.returncode, race.stdout, race.stderr)
        assert "refusing to cache or publish mixed-provenance output" in race.stderr, race.stderr
        assert mutation_marker.exists(), "mock compiler did not mutate during compilation"
        assert not object_cache.exists() or not any(object_cache.iterdir()), list(object_cache.glob("**/*"))
        assert not (race_outputs / "elisa-proof").exists()
        assert not (race_outputs / "elisa-proof-replay").exists()
        assert (proof / "build/elisa-proof-generations/CURRENT").read_text() == current_generation
        generations_after = {
            path.name for path in (proof / "build/elisa-proof-generations").iterdir()
            if path.is_dir()
        }
        assert generations_after == generations_before, (generations_before, generations_after)
        print("build provenance races: source mutation stayed snapshot-isolated; compiler mutation "
              "failed closed before cache or generation publication")


if __name__ == "__main__":
    main()
