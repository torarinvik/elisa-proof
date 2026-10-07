"""Concurrent mocked builds must stay inside their independent proof roots."""

from __future__ import annotations

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
    "build.sh", "compiler_snapshot.sh", "compiler_provenance.sh", "link_flags.sh", "platform.sh", "runtime_inputs.sh",
    "build_manifest.py", "compiler_environment.py", "verify_product_pair.py",
)


def executable(path: Path, contents: str) -> None:
    path.write_text(contents)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def make_compiler_source(root: Path, label: str) -> str:
    for directory in (root / "src", root / "elisacore_std", root / "test/parity"):
        directory.mkdir(parents=True, exist_ok=True)
    (root / "src/front.elisa").write_text(f"frontend {label}\n")
    (root / "elisacore_std/placeholder").write_text(f"stdlib {label}\n")
    (root / "test/parity/profile_hooks.c").write_text("void profile_hook(void) {}\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Build test",
         "-c", "user.email=build-test@example.invalid", "commit", "-qm", label],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def make_fixture(base: Path, tag: str, shared_tools: Path) -> tuple[Path, dict[str, str]]:
    project = base / tag
    proof = project / "proof"
    compiler_source = project / "compiler-source"
    for directory in (proof / "scripts", proof / "src", proof / "examples"):
        directory.mkdir(parents=True, exist_ok=True)
    for name in BUILD_SCRIPTS:
        shutil.copy2(ROOT / "scripts" / name, proof / "scripts" / name)

    # The only pause is after the first staged manifest has been written. This
    # keeps both builds at the same deterministic point while we inspect paths.
    manifest_tool = proof / "scripts/build_manifest.py"
    source = manifest_tool.read_text()
    source = source.replace(
        "        handle.write(\"\\n\")\n    return 0\n",
        "        handle.write(\"\\n\")\n"
        "    if os.environ.get(\"MOCK_MANIFEST_GATE\") == \"1\":\n"
        "        marker = __import__(\"pathlib\").Path(os.environ[\"MOCK_MANIFEST_GATE_DIR\"]) / (\"manifest-\" + os.environ[\"MOCK_ROOT_TAG\"])\n"
        "        marker.write_text(arguments.output)\n"
        "        while not __import__(\"pathlib\").Path(os.environ[\"MOCK_MANIFEST_RELEASE\"]).exists():\n"
        "            __import__(\"time\").sleep(0.01)\n"
        "    return 0\n",
    )
    assert source != manifest_tool.read_text(), "manifest gate insertion point changed"
    manifest_tool.write_text(source)

    revision = make_compiler_source(compiler_source, f"frontend-{tag}")
    (proof / "src/main.elisa").write_text(
        f'include "../../Elisa-compiler/src/front.elisa"\nmain {tag}\n'
    )
    (proof / "src/replay_main.elisa").write_text(
        f'include "../../Elisa-compiler/src/front.elisa"\nreplay {tag}\n'
    )
    (proof / "examples/fixture.elisa").write_text(f"fixture {tag}\n")

    environment = dict(
        os.environ,
        ELISA_COMPILER_BIN=str(shared_tools / "mock-elisac"),
        ELISA_COMPILER_SRC=str(compiler_source),
        ELISA_COMPILER_REV=revision,
        ELISA_CLANG=str(shared_tools / "clang"),
        ELISA_PROOF_PRODUCTS="all",
        ELISA_PROOF_OBJECT_CACHE="0",
        MOCK_MANIFEST_GATE="1",
        MOCK_MANIFEST_GATE_DIR=str(base / "gate"),
        MOCK_MANIFEST_RELEASE=str(base / "gate/release"),
        MOCK_ROOT_TAG=tag,
        PATH=str(shared_tools) + os.pathsep + os.environ["PATH"],
    )
    return proof, environment


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="elisa-build-independent-roots-") as directory:
        base = Path(directory)
        tools = base / "tools"
        gate = base / "gate"
        tools.mkdir()
        gate.mkdir()
        executable(tools / "mock-elisac", """#!/usr/bin/env python3
import os, pathlib, sys
args = sys.argv[1:]
output = pathlib.Path(args[args.index('-o') + 1])
source = pathlib.Path(args[-1])
output.write_text(os.environ['MOCK_ROOT_TAG'] + ':' + source.name + ':' + source.read_text())
""")
        executable(tools / "clang", """#!/usr/bin/env python3
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
    output.write_bytes(os.environ['MOCK_ROOT_TAG'].encode() + b':fixture-link:' + str(output.name).encode())
""")
        executable(tools / "uname", """#!/bin/sh
if [ "$1" = "-smr" ]; then
    printf 'fixture-system fixture-machine %s\\n' "$MOCK_UNAME_RELEASE"
else
    printf 'fixture-system\\n'
fi
""")

        fixtures = [make_fixture(base, tag, tools) for tag in ("root-a", "root-b")]
        processes: list[subprocess.Popen] = []
        release = gate / "release"
        try:
            for proof, environment in fixtures:
                processes.append(subprocess.Popen(
                    [str(proof / "scripts/build.sh")], cwd=proof, env=environment,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                ))

            deadline = time.monotonic() + 30
            markers = [gate / f"manifest-{tag}" for tag in ("root-a", "root-b")]
            while not all(marker.exists() for marker in markers) and time.monotonic() < deadline:
                for process in processes:
                    if process.poll() is not None:
                        stdout, stderr = process.communicate()
                        raise AssertionError(f"build exited before manifest barrier: {stdout}\n{stderr}")
                time.sleep(0.01)
            assert all(marker.exists() for marker in markers), "both builds did not reach manifest barrier"

            staged_artifacts: list[set[Path]] = []
            staged_manifests: list[dict] = []
            for (proof, _environment), process, marker in zip(fixtures, processes, markers):
                build = proof / "build"
                lock = build / ".elisa-proof-build.lock"
                assert lock.is_dir(), f"missing root-local lock: {lock}"
                assert (lock / "pid").read_text().strip() == str(process.pid)
                pid = process.pid
                expected = {
                    lock,
                    build / f"elisa-proof-stage.{pid}.0.o",
                    build / f"elisa-proof-stage.{pid}.1.o",
                    build / f"elisa-proof.{pid}.0",
                    build / f"elisa-proof.{pid}.0.manifest.json",
                }
                missing = [path for path in expected if path != lock and not path.exists()]
                assert not missing, f"missing staged artifacts: {missing}"
                tag = _environment["MOCK_ROOT_TAG"]
                for index in (0, 1):
                    staged_object = build / f"elisa-proof-stage.{pid}.{index}.o"
                    assert staged_object.read_text().startswith(tag + ":"), staged_object
                staged_binary = build / f"elisa-proof.{pid}.0"
                assert staged_binary.read_bytes().startswith(tag.encode() + b":fixture-link:"), staged_binary
                manifest_path = Path(marker.read_text())
                assert manifest_path == build / f"elisa-proof.{pid}.0.manifest.json"
                manifest = json.loads(manifest_path.read_text())
                assert manifest["pair_generation"]
                assert manifest["proof"]["source_tree_sha256"]
                staged_artifacts.append(expected)
                staged_manifests.append(manifest)

            assert staged_artifacts[0].isdisjoint(staged_artifacts[1]), staged_artifacts
            assert staged_manifests[0]["pair_generation"] != staged_manifests[1]["pair_generation"]
            assert staged_manifests[0]["proof"]["source_tree_sha256"] != staged_manifests[1]["proof"]["source_tree_sha256"]
            assert staged_manifests[0]["frontend"]["revision"] != staged_manifests[1]["frontend"]["revision"]

        finally:
            release.touch()
            for process in processes:
                if process.poll() is None:
                    process.communicate(timeout=60)

        for fixture_index, ((proof, _environment), process) in enumerate(zip(fixtures, processes)):
            stdout, stderr = process.communicate()
            assert process.returncode == 0, (process.returncode, stdout, stderr)
            build = proof / "build"
            assert not (build / ".elisa-proof-build.lock").exists()
            generation_root = build / "elisa-proof-generations"
            current = (generation_root / "CURRENT").read_text().strip()
            assert current == staged_manifests[fixture_index]["pair_generation"]
            resolved = subprocess.run(
                ["python3", str(proof / "scripts/verify_product_pair.py"), "resolve",
                 "--generation-root", str(generation_root)],
                check=True, capture_output=True, text=True,
            )
            pair = json.loads(resolved.stdout)
            assert pair["pair_generation"] == current
            products = pair["products"]
            assert set(products) == {"elisa-proof", "elisa-proof-replay"}
            manifests = [json.loads(Path(products[name]["manifest"]).read_text())
                         for name in ("elisa-proof", "elisa-proof-replay")]
            assert all(manifest["pair_generation"] == current for manifest in manifests)
            assert manifests[0]["proof"] == manifests[1]["proof"]
            generation_dir = (generation_root / current).resolve()
            assert all(Path(row["binary"]).is_relative_to(generation_dir)
                       for row in products.values())

        generations = [manifest["pair_generation"] for manifest in staged_manifests]
        assert generations[0] != generations[1]
        print("independent-root build coordination: concurrent mocked builds used distinct locks, "
              "staging/manifests, source identities and pair generations; both generation pairs resolve")


if __name__ == "__main__":
    main()
