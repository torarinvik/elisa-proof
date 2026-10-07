"""Stage1 product and imported-frontend identities must be the same commit/tree."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_manifest  # noqa: E402


def commit(root: Path, message: str) -> str:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Provenance test",
         "-c", "user.email=provenance-test@example.invalid", "commit", "-qm", message],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def write_provenance(root: Path, product: Path, revision: str, *, source_tree: str | None = None) -> None:
    if source_tree is None:
        source_tree = build_manifest.committed_compiler_source_digest(str(root), revision)
    product_digest = hashlib.sha256(product.read_bytes()).hexdigest()
    (Path(str(product) + ".provenance.json")).write_text(json.dumps({
        "schema": "elisa-stage1-provenance-v1",
        "source_revision": revision,
        "source_tree_sha256": source_tree,
        "build_recipe_sha256": build_manifest.committed_compiler_recipe_digest(str(root), revision),
        "product_sha256": product_digest,
    }))


def make_compiler(root: Path, *, installed_snapshot: bool) -> tuple[str, Path]:
    (root / "src").mkdir(parents=True)
    (root / "elisacore_std").mkdir()
    (root / "src/front.elisa").write_text("frontend v1\n")
    (root / "elisacore_std/prelude.elisa").write_text("stdlib v1\n")
    for recipe in (
        "scripts/elisac_stage1.sh", "scripts/elisac_stage1_seed.sh",
        "scripts/build_runtime_object.sh", "scripts/write_profiler_hook_fallbacks.sh",
    ):
        path = root / recipe
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# fixture: {recipe}\n")
    (root / "scripts/stage1_provenance.py").write_text(
        "BUILD_RECIPES = ('scripts/elisac_stage1.sh', "
        "'scripts/elisac_stage1_seed.sh', 'scripts/build_runtime_object.sh', "
        "'scripts/write_profiler_hook_fallbacks.sh')\n"
    )
    revision = commit(root, "frontend baseline")
    product = root / "bin/elisac-stage1"
    product.parent.mkdir()
    product.write_bytes(b"mock stage1 product\n")
    write_provenance(root, product, revision)
    if installed_snapshot:
        (root / "SNAPSHOT").write_text(
            f"revision: {revision[:8]}\nsource_revision: {revision}\n"
        )
    return revision, product


def executable(path: Path, contents: str) -> None:
    path.write_text(contents)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def run_stage1_build(base: Path, *, installed_snapshot: bool) -> dict:
    proof = base / "proof"
    compiler = base / "compiler"
    tools = base / "tools"
    for directory in (proof / "scripts", proof / "src", proof / "examples",
                      compiler / "src", compiler / "elisacore_std",
                      compiler / "scripts",
                      compiler / "test/parity", compiler / "scripts",
                      compiler / "build/runtime", tools):
        directory.mkdir(parents=True, exist_ok=True)
    for name in ("build.sh", "compiler_snapshot.sh", "compiler_provenance.sh",
                 "link_flags.sh", "build_manifest.py", "compiler_environment.py",
                 "verify_product_pair.py", "runtime_inputs.sh", "compiler_recipe_inputs.py"):
        shutil.copy2(ROOT / "scripts" / name, proof / "scripts" / name)
    (compiler / "src/front.elisa").write_text("pinned frontend\n")
    (compiler / "elisacore_std/prelude.elisa").write_text("pinned stdlib\n")
    for recipe in (
        "scripts/elisac_stage1.sh", "scripts/elisac_stage1_seed.sh",
        "scripts/build_runtime_object.sh", "scripts/write_profiler_hook_fallbacks.sh",
    ):
        (compiler / recipe).write_text(f"# fixture: {recipe}\n")
    (compiler / "test/parity/profile_hooks.c").write_text("void profile_hook(void) {}\n")
    (compiler / "build/runtime/elisacore_runtime.o").write_bytes(b"runtime object")
    wrapper = compiler / "scripts/elisac_stage1.sh"
    executable(wrapper, "#!/bin/sh\nexec \"$(dirname \"$0\")/../bin/elisac-stage1\" \"$@\"\n")
    (compiler / "scripts/stage1_provenance.py").write_text(
        "BUILD_RECIPES = ('scripts/elisac_stage1.sh', "
        "'scripts/elisac_stage1_seed.sh', 'scripts/build_runtime_object.sh', "
        "'scripts/write_profiler_hook_fallbacks.sh')\n"
    )
    revision = commit(compiler, "Stage1 build fixture")
    product = compiler / "bin/elisac-stage1"
    product.parent.mkdir()
    executable(product, """#!/usr/bin/env python3
import pathlib, sys
args = sys.argv[1:]
pathlib.Path(args[args.index('-o') + 1]).write_bytes(b'compiled object')
""")
    write_provenance(compiler, product, revision)
    if installed_snapshot:
        (compiler / "SNAPSHOT").write_text(
            f"revision: {revision[:8]}\nsource_revision: {revision}\n"
        )

    (proof / "src/main.elisa").write_text(
        'include "../../Elisa-compiler/src/front.elisa"\nmain\n'
    )
    (proof / "examples/fixture.elisa").write_text("fixture\n")
    executable(tools / "clang", """#!/usr/bin/env python3
import pathlib, sys
args = sys.argv[1:]
if args == ['--version']:
    print('fixture clang 1')
elif args == ['-dumpmachine']:
    print('x86_64-fixture-linux')
elif args == ['-print-resource-dir']:
    print('/fixture/clang/resources')
else:
    pathlib.Path(args[args.index('-o') + 1]).write_bytes(b'linked executable')
""")
    executable(tools / "uname", """#!/bin/sh
if [ "$1" = "-smr" ]; then printf 'Linux fixture 1\\n'; else printf 'Linux\\n'; fi
""")
    environment = dict(
        os.environ,
        HOME=str(base / "home"),
        ELISA_COMPILER_BIN=str(wrapper),
        ELISA_COMPILER_SRC=str(compiler),
        ELISA_COMPILER_REV=revision,
        ELISA_CLANG=str(tools / "clang"),
        ELISA_PROOF_OBJECT_CACHE="0",
        PATH=str(tools) + os.pathsep + os.environ["PATH"],
    )
    (base / "home").mkdir()
    result = subprocess.run(
        ["bash", str(proof / "scripts/build.sh")], cwd=proof,
        env=environment, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AssertionError(f"mock Stage1 build failed:\n{result.stdout}\n{result.stderr}")
    manifest = json.loads((proof / "build/elisa-proof.manifest.json").read_text())
    assert manifest["compiler"]["stage1_revision"] == revision
    assert manifest["compiler"]["source_revision"] == revision
    assert manifest["compiler"]["source_tree_sha256"] == build_manifest.committed_compiler_source_digest(
        str(compiler), revision,
    )
    assert manifest["compiler"]["build_recipe_sha256"] == build_manifest.committed_compiler_recipe_digest(
        str(compiler), revision,
    )
    assert manifest["frontend"]["revision"] == revision
    return manifest


class Stage1BuildProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="elisa-stage1-manifest-")
        self.root = Path(self.temporary.name) / "compiler"
        self.root.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def resolve(self, root: Path, revision: str, product: Path) -> str:
        return build_manifest.stage1_provenance_revision(
            str(product), str(root), str(root), revision,
        )

    def test_source_worktree_without_snapshot_resolves_exact_full_commit(self) -> None:
        revision, product = make_compiler(self.root, installed_snapshot=False)
        self.assertFalse((self.root / "SNAPSHOT").exists())
        self.assertEqual(self.resolve(self.root, revision, product), revision)

    def test_installed_snapshot_and_product_provenance_must_agree(self) -> None:
        revision, product = make_compiler(self.root, installed_snapshot=True)
        self.assertEqual(self.resolve(self.root, revision, product), revision)
        (self.root / "SNAPSHOT").write_text(
            f"revision: deadbeef\nsource_revision: {'d' * 40}\n"
        )
        with self.assertRaisesRegex(ValueError, "snapshot revision"):
            self.resolve(self.root, revision, product)

    def test_missing_and_stale_product_provenance_fail_closed(self) -> None:
        revision, product = make_compiler(self.root, installed_snapshot=False)
        sidecar = Path(str(product) + ".provenance.json")
        sidecar.unlink()
        with self.assertRaisesRegex(ValueError, "provenance unavailable"):
            self.resolve(self.root, revision, product)
        write_provenance(self.root, product, revision)
        product.write_bytes(b"rebuilt without refreshing provenance\n")
        with self.assertRaisesRegex(ValueError, "product is stale"):
            self.resolve(self.root, revision, product)

    def test_revision_and_source_tree_mismatches_fail_closed(self) -> None:
        revision, product = make_compiler(self.root, installed_snapshot=False)
        (self.root / "src/front.elisa").write_text("frontend v2\n")
        next_revision = commit(self.root, "new frontend")
        with self.assertRaisesRegex(ValueError, "stage1/frontend provenance mismatch"):
            self.resolve(self.root, next_revision, product)

        write_provenance(self.root, product, next_revision, source_tree="c" * 64)
        with self.assertRaisesRegex(ValueError, "source-tree digest"):
            self.resolve(self.root, next_revision, product)

    def test_source_worktree_head_must_match_product_provenance(self) -> None:
        revision, product = make_compiler(self.root, installed_snapshot=False)
        (self.root / "src/front.elisa").write_text("frontend v2\n")
        commit(self.root, "advance compiler checkout")
        with self.assertRaisesRegex(ValueError, "source-worktree commit"):
            self.resolve(self.root, revision, product)

    def test_manifest_records_full_revision_from_source_product_sidecar(self) -> None:
        revision, product = make_compiler(self.root, installed_snapshot=False)
        proof_binary = self.root / "proof-output"
        proof_binary.write_bytes(b"proof executable")
        runtime = self.root / "runtime.o"
        runtime.write_bytes(b"runtime")
        hooks = self.root / "hooks.o"
        hooks.write_bytes(b"hooks")
        manifest_path = self.root / "manifest.json"
        args = [
            sys.executable, str(ROOT / "scripts/build_manifest.py"),
            "--binary", str(proof_binary), "--compiler", str(product),
            "--compiler-product", str(product), "--compiler-root", str(self.root),
            "--stage", "stage1", "--stage1-revision", "", "--runtime", str(runtime),
            "--profile-hooks", str(hooks), "--frontend-repo", str(self.root),
            "--frontend-revision", revision, "--proof-root", str(self.root),
            "--snapshot-root", str(self.root), "--opt-level", "O0",
            "--compile-mode", "strict", "--contract-flag", "",
            "--installed-as", str(proof_binary), "--output", str(manifest_path),
        ]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["compiler"]["stage1_revision"], revision)

    def test_build_script_records_source_worktree_and_installed_snapshot_revisions(self) -> None:
        source_case = run_stage1_build(Path(self.temporary.name) / "source", installed_snapshot=False)
        self.assertEqual(source_case["compiler"]["stage"], "stage1")
        installed_case = run_stage1_build(
            Path(self.temporary.name) / "installed", installed_snapshot=True,
        )
        self.assertEqual(installed_case["compiler"]["stage"], "stage1")


if __name__ == "__main__":
    unittest.main()
