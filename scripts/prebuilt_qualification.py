#!/usr/bin/env python3
"""Fail closed before tests reuse prebuilt proof/replay products.

The normal test path builds from the current snapshot. ``ELISA_PROOF_SKIP_BUILD=1`` is
useful on remote runners, but it must not turn an old executable into evidence for a newer
source tree or compiler pin. This check binds both published binaries to the current source
snapshot and verifies the compiler/runtime artifacts named by their manifests.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import sys
from pathlib import Path

from build_manifest_hashes import tree_digest
from build_manifest import stage1_provenance_revision
from perf_build_provenance import require_clean_toolchain, verify_build_artifacts
from stage1_provenance_validation import validate_stage0_build_info
from verify_product_pair import resolve_pair_with_manifests


PRODUCTS = ("elisa-proof", "elisa-proof-replay")


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _pinned_compiler_archive(compiler_repository: Path, revision: str) -> bytes:
    """Return the exact files compiler_snapshot.sh exports for a pinned commit."""
    result = subprocess.run(
        ["git", "-C", str(compiler_repository), "archive", "--format=tar", revision,
         "src", "elisacore_std", "test/parity/profile_hooks.c"],
        check=True, capture_output=True,
    )
    return result.stdout


def validate_compiler_snapshot_tree(snapshot_root: Path, archive: bytes) -> str:
    """Compare every exported snapshot file against the pinned Git archive.

    ``.rev`` is a locator, not evidence that the source files beside it are intact.
    Reject extra files and symlinks as well as altered/missing archive entries.
    """
    if snapshot_root.is_symlink():
        raise ValueError("compiler snapshot is not a regular directory")
    snapshot_root = snapshot_root.resolve()
    expected: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as pinned:
            for member in pinned.getmembers():
                if member.isdir():
                    continue
                relative = member.name.rstrip("/")
                parts = Path(relative).parts
                if (not member.isfile() or Path(relative).is_absolute()
                        or ".." in parts or not relative
                        or relative in expected):
                    raise ValueError("pinned compiler archive contains an unsupported or duplicate path")
                stream = pinned.extractfile(member)
                if stream is None:
                    raise ValueError(f"cannot read pinned compiler snapshot file {relative}")
                expected[relative] = stream.read()
    except tarfile.TarError as error:
        raise ValueError(f"cannot read pinned compiler source archive: {error}") from error
    if not expected:
        raise ValueError("pinned compiler source archive is empty")

    observed: dict[str, bytes] = {}
    if not snapshot_root.is_dir() or snapshot_root.is_symlink():
        raise ValueError("compiler snapshot is not a regular directory")
    for directory, subdirectories, filenames in os.walk(snapshot_root, followlinks=False):
        base = Path(directory)
        for name in list(subdirectories):
            path = base / name
            if path.is_symlink():
                raise ValueError(f"compiler snapshot contains a symlink: {path.relative_to(snapshot_root)}")
        for name in filenames:
            path = base / name
            relative = path.relative_to(snapshot_root).as_posix()
            if relative == ".rev":
                if path.is_symlink() or not path.is_file():
                    raise ValueError("compiler snapshot revision marker is not a regular file")
                continue
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"compiler snapshot contains a non-regular file: {relative}")
            observed[relative] = path.read_bytes()

    missing = sorted(expected.keys() - observed.keys())
    extra = sorted(observed.keys() - expected.keys())
    if missing or extra:
        raise ValueError(
            "compiler snapshot file set differs from pinned Git archive"
            f" (missing={missing[:3]}, extra={extra[:3]})"
        )
    for relative in sorted(expected):
        if observed[relative] != expected[relative]:
            raise ValueError(f"compiler snapshot file differs from pinned Git archive: {relative}")

    digest = hashlib.sha256()
    for relative in sorted(observed):
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(observed[relative]).digest())
    return digest.hexdigest()


def validate_source_metadata(
    manifests: dict[str, dict], source_root: Path, snapshot_root: Path,
    head: str, source_dirty: bool,
) -> str:
    """Require each binary to name the exact current proof source snapshot."""
    source_digest = tree_digest(str(source_root))
    snapshot_digest = tree_digest(str(snapshot_root))
    if source_digest != snapshot_digest:
        raise ValueError("compiler snapshot source differs from the current proof source tree")
    for role, manifest in manifests.items():
        proof = manifest.get("proof")
        if not isinstance(proof, dict):
            raise ValueError(f"{role} manifest has no proof-source identity")
        if proof.get("head") != head:
            raise ValueError(f"{role} binary was built from a different proof HEAD")
        if proof.get("source_dirty") is not source_dirty:
            raise ValueError(f"{role} manifest has stale proof-source cleanliness metadata")
        if proof.get("source_tree_sha256") != source_digest:
            raise ValueError(f"{role} binary does not match the current proof source tree")
    return source_digest


def validate_frontend_metadata(
    manifests: dict[str, dict], snapshot_revision: str,
    pinned_frontend_revision: str, pinned_stage0_revision: str,
    expected_frontend_tree: str,
) -> str:
    """Require the compiler recorded by both products to match the checked-in pins."""
    if re.fullmatch(r"[0-9a-f]{40}", snapshot_revision) is None:
        raise ValueError("compiler snapshot has no exact source revision")
    if (re.fullmatch(r"[0-9a-f]{40}", pinned_frontend_revision) is None
            or snapshot_revision != pinned_frontend_revision):
        raise ValueError("compiler snapshot revision does not match ELISA_COMPILER_REV")
    if re.fullmatch(r"[0-9a-f]{40}", pinned_stage0_revision) is None:
        raise ValueError("ELISA_STAGE0_REV must be an exact 40-character commit hash")

    for role, manifest in manifests.items():
        frontend = manifest.get("frontend")
        compiler = manifest.get("compiler")
        if not isinstance(frontend, dict) or not isinstance(compiler, dict):
            raise ValueError(f"{role} manifest has incomplete frontend/compiler provenance")
        if frontend.get("revision") != snapshot_revision:
            raise ValueError(f"{role} binary was built against a different frontend revision")
        if frontend.get("tree") != expected_frontend_tree:
            raise ValueError(f"{role} binary was built against a different frontend source tree")
        stage = compiler.get("stage")
        if stage == "stage1":
            if compiler.get("source_dirty") is not False:
                raise ValueError(f"{role} Stage1 compiler source was dirty or its cleanliness is unknown")
            if compiler.get("stage1_revision") != snapshot_revision:
                raise ValueError(f"{role} Stage1 product does not match the pinned frontend")
            if compiler.get("source_revision") != snapshot_revision:
                raise ValueError(f"{role} Stage1 source revision does not match its product")
        elif stage == "stage0":
            stage0_source_revision = compiler.get("source_revision")
            if compiler.get("source_dirty") is not None and compiler.get("source_dirty") is not False:
                raise ValueError(f"{role} Stage0 source is recorded as dirty")
            if (stage0_source_revision is not None
                    and (not isinstance(stage0_source_revision, str)
                         or re.fullmatch(r"[0-9a-f]{40}", stage0_source_revision) is None
                         or not pinned_stage0_revision
                         or stage0_source_revision != pinned_stage0_revision)):
                raise ValueError(f"{role} Stage0 source revision does not match ELISA_STAGE0_REV")
        else:
            raise ValueError(f"{role} manifest names an unsupported compiler stage")
    return str(manifests[PRODUCTS[0]]["compiler"]["stage"])


def verify_stage0_binary(manifest: dict, pinned_revision: str, label: str) -> str:
    compiler = manifest.get("compiler", {})
    product = compiler.get("product", {})
    path = product.get("path") if isinstance(product, dict) else None
    if not isinstance(path, str) or not path:
        raise ValueError(f"{label} manifest has no Stage0 product path")
    result = subprocess.run(
        ["go", "version", "-m", path], check=True, capture_output=True, text=True,
    )
    return validate_stage0_build_info(result.stdout, pinned_revision)


def _read_pair(root: Path) -> tuple[str, dict[str, dict], dict[str, Path]]:
    generation_root = root / "build/elisa-proof-generations"
    resolved, manifests = resolve_pair_with_manifests(generation_root)
    generation = resolved["pair_generation"]
    if re.fullmatch(r"[0-9a-f]{32}", generation) is None:
        raise ValueError("CURRENT has an invalid product generation identity")
    binaries = {
        name: Path(resolved["products"][name]["binary"])
        for name in PRODUCTS
    }
    return generation, manifests, binaries


def qualify_prebuilt(root: Path, snapshot_root: Path, compiler_snapshot: Path,
                     compiler_repository: Path) -> dict:
    generation, manifests, binaries = _read_pair(root)
    proof = manifests[PRODUCTS[0]].get("proof", {})
    source_head = _git(root, "rev-parse", "HEAD")
    source_dirty = bool(_git(root, "status", "--porcelain", "--", "src"))
    source_digest = validate_source_metadata(
        manifests, root / "src", snapshot_root / "src", source_head, source_dirty,
    )
    snapshot_revision = (compiler_snapshot / ".rev").read_text(encoding="ascii").strip()
    frontend_pin = (root / "ELISA_COMPILER_REV").read_text(encoding="ascii").strip()
    stage0_pin = (root / "ELISA_STAGE0_REV").read_text(encoding="ascii").strip()
    frontend_tree = _git(compiler_repository, "rev-parse", f"{snapshot_revision}^{{tree}}")
    compiler_stage = validate_frontend_metadata(
        manifests, snapshot_revision, frontend_pin, stage0_pin, frontend_tree,
    )
    compiler_snapshot_digest = validate_compiler_snapshot_tree(
        compiler_snapshot,
        _pinned_compiler_archive(compiler_repository, snapshot_revision),
    )
    if compiler_stage == "stage1":
        require_clean_toolchain(manifests, "prebuilt test product pair")
    else:
        for role, manifest in manifests.items():
            verify_stage0_binary(manifest, stage0_pin, role)
    for role, manifest in manifests.items():
        verify_build_artifacts(manifest, f"prebuilt/{role}")
        if compiler_stage == "stage1":
            compiler = manifest["compiler"]
            product_path = compiler["product"]["path"]
            compiler_root = Path(product_path).resolve().parent.parent
            product_revision = stage1_provenance_revision(
                product_path, str(compiler_root), str(compiler_repository), snapshot_revision,
                pinned_stage0_revision=stage0_pin,
                require_stage0_binding=True,
            )
            if product_revision != snapshot_revision:
                raise ValueError(f"{role} Stage1 product source differs from the pinned frontend")
    return {
        "generation": generation,
        "proof_binary": str(binaries[PRODUCTS[0]]),
        "replay_binary": str(binaries[PRODUCTS[1]]),
        "proof_source_head": source_head,
        "proof_source_dirty": proof["source_dirty"],
        "proof_source_tree_sha256": source_digest,
        "frontend_revision": snapshot_revision,
        "frontend_snapshot_sha256": compiler_snapshot_digest,
        "compiler_stage": compiler_stage,
        "proof_binary_sha256": manifests[PRODUCTS[0]]["binary"]["sha256"],
        "replay_binary_sha256": manifests[PRODUCTS[1]]["binary"]["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof-root", required=True, type=Path)
    parser.add_argument("--snapshot-root", required=True, type=Path)
    parser.add_argument("--compiler-snapshot", required=True, type=Path)
    parser.add_argument("--compiler-repository", required=True, type=Path)
    parser.add_argument("--json", action="store_true", help="emit only the qualification JSON object")
    arguments = parser.parse_args()
    try:
        result = qualify_prebuilt(
            arguments.proof_root.resolve(), arguments.snapshot_root.resolve(),
            arguments.compiler_snapshot.absolute(), arguments.compiler_repository.resolve(),
        )
    except (OSError, ValueError, subprocess.CalledProcessError, KeyError) as error:
        print(f"prebuilt qualification refused: {error}", file=sys.stderr)
        return 2
    encoded = json.dumps(result, sort_keys=True)
    print(encoded if arguments.json else "prebuilt qualification: " + encoded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
