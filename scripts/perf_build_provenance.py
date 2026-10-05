"""Build identity checks shared by reproducible proof benchmarks."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path


def file_identity(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def source_tree_identity(root: Path) -> str:
    """Hash a proof `src` tree exactly like build_manifest.tree_digest."""
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise RuntimeError(f"source tree is not a directory: {root}")
    digest = hashlib.sha256()
    for directory, subdirectories, files in os.walk(root):
        subdirectories.sort()
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            file_hash = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    file_hash.update(block)
            digest.update(relative.encode("utf-8") + b"\0")
            digest.update(file_hash.digest())
    return digest.hexdigest()


def read_build_manifest(binary: Path, label: str) -> dict:
    manifest_path = Path(str(binary) + ".manifest.json")
    checksum_path = Path(str(manifest_path) + ".sha256")
    try:
        manifest_bytes = manifest_path.read_bytes()
        recorded_checksum = checksum_path.read_text(encoding="ascii").strip()
        manifest = json.loads(manifest_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} build manifest is missing or invalid: {error}") from error
    if recorded_checksum != hashlib.sha256(manifest_bytes).hexdigest():
        raise RuntimeError(f"{label} build manifest checksum does not match its sidecar")
    if not isinstance(manifest, dict):
        raise RuntimeError(f"{label} build manifest is not a JSON object")
    binary_identity = manifest.get("binary", {})
    if (not isinstance(binary_identity, dict)
            or binary_identity.get("sha256") != file_identity(binary)["sha256"]):
        raise RuntimeError(f"{label} build manifest does not identify the supplied executable")
    return manifest


def shared_product_context(manifest: dict) -> dict:
    """Fields that must match when proof and replay products share a build snapshot."""
    proof = manifest.get("proof", {})
    frontend = manifest.get("frontend", {})
    compiler = manifest.get("compiler", {})
    runtime = manifest.get("runtime", {})
    hooks = manifest.get("profile_hooks", {})
    nested = (proof, frontend, compiler, runtime, hooks)
    if any(not isinstance(value, dict) for value in nested):
        raise RuntimeError("build manifest has a malformed shared identity object")
    compiler_product = compiler.get("product", {})
    compiler_executable = compiler.get("executable", {})
    if not isinstance(compiler_product, dict) or not isinstance(compiler_executable, dict):
        raise RuntimeError("build manifest has malformed compiler identity fields")
    return {
        "proof.source_tree_sha256": proof.get("source_tree_sha256"),
        "frontend.revision": frontend.get("revision"),
        "frontend.tree": frontend.get("tree"),
        "compiler.stage": compiler.get("stage"),
        "compiler.stage1_revision": compiler.get("stage1_revision"),
        "compiler.source_revision": compiler.get("source_revision"),
        "compiler.source_dirty": compiler.get("source_dirty"),
        "compiler.product.sha256": compiler_product.get("sha256"),
        "compiler.executable.sha256": compiler_executable.get("sha256"),
        "runtime.sha256": runtime.get("sha256"),
        "profile_hooks.sha256": hooks.get("sha256"),
        "target": manifest.get("target"),
        "optimization": manifest.get("optimization"),
        "compile_mode": manifest.get("compile_mode"),
        "compiler_flags": manifest.get("compiler_flags"),
    }


def require_compatible_products(proof_manifest: dict, replay_manifest: dict,
                                label: str) -> dict:
    proof_context = shared_product_context(proof_manifest)
    replay_context = shared_product_context(replay_manifest)
    differences = [key for key in proof_context if proof_context[key] != replay_context[key]]
    optional = {"profile_hooks.sha256", "compiler.stage1_revision"}
    if proof_context["compiler.stage"] == "stage0":
        optional.add("runtime.sha256")
    missing = [key for key, value in proof_context.items()
               if value is None and key not in optional]
    missing.extend(key for key, value in replay_context.items()
                   if value is None and key not in optional)
    if differences or missing:
        details = sorted(set(differences + missing))
        raise RuntimeError(f"{label} proof/replay products have incompatible build provenance: {details}")
    return proof_context


def verify_build_artifacts(manifest: dict, label: str) -> None:
    """Re-hash linked/build-tool files instead of trusting path/hash strings in JSON."""
    compiler = manifest.get("compiler", {})
    artifacts = {
        "compiler executable": compiler.get("executable"),
        "compiler product": compiler.get("product"),
        "runtime": manifest.get("runtime"),
        "profile hooks": manifest.get("profile_hooks"),
    }
    for name, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            raise RuntimeError(f"{label} manifest has no {name} identity")
        path, expected = artifact.get("path"), artifact.get("sha256")
        if expected is None and path is None and (
                name == "profile hooks"
                or name == "runtime" and compiler.get("stage") == "stage0"):
            continue
        if not isinstance(path, str) or not path or not isinstance(expected, str):
            raise RuntimeError(f"{label} manifest lacks the {name} path or digest")
        try:
            observed = file_identity(Path(path))["sha256"]
        except OSError as error:
            raise RuntimeError(f"{label} {name} is unavailable: {error}") from error
        if observed != expected:
            raise RuntimeError(f"{label} {name} no longer matches its manifest digest")


def verify_proof_source(manifests: dict, root: Path, expected_sha256: str, label: str) -> str:
    """Verify an explicitly named source snapshot against both manifests and disk."""
    if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
            or any(character not in "0123456789abcdef" for character in expected_sha256)):
        raise RuntimeError(f"{label} requires an exact lowercase SHA-256 source-tree hash")
    observed = source_tree_identity(root)
    if observed != expected_sha256:
        raise RuntimeError(f"{label} source tree hash does not match the supplied expected hash")
    for role, manifest in manifests.items():
        proof = manifest.get("proof")
        if not isinstance(proof, dict) or proof.get("source_tree_sha256") != observed:
            raise RuntimeError(f"{label}/{role} manifest does not identify the verified source tree")
        if proof.get("source_dirty") not in (False, True):
            raise RuntimeError(f"{label}/{role} manifest is missing proof source cleanliness")
    return observed


def require_clean_toolchain(manifests: dict, label: str) -> None:
    """A dirty compiler cannot be attested by proof-source hashes alone."""
    for role, manifest in manifests.items():
        compiler = manifest.get("compiler")
        if not isinstance(compiler, dict) or compiler.get("source_dirty") is not False:
            raise RuntimeError(
                f"{label}/{role} compiler source is dirty or cleanliness is unknown; "
                "rebuild from a clean compiler snapshot"
            )


def manifest_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="elisa-perf-manifest-self-test-") as temporary:
        binary = Path(temporary) / "proof"
        binary.write_bytes(b"proof binary")
        manifest_path = Path(str(binary) + ".manifest.json")
        checksum_path = Path(str(manifest_path) + ".sha256")
        manifest = {"binary": {"sha256": file_identity(binary)["sha256"]}}
        manifest_bytes = json.dumps(manifest).encode()
        manifest_path.write_bytes(manifest_bytes)
        checksum_path.write_text(hashlib.sha256(manifest_bytes).hexdigest(), encoding="ascii")
        if read_build_manifest(binary, "self-test") != manifest:
            raise RuntimeError("build manifest reader changed a valid manifest")
        checksum_path.write_text("0" * 64, encoding="ascii")
        try:
            read_build_manifest(binary, "self-test")
        except RuntimeError as error:
            if "checksum" not in str(error):
                raise
        else:
            raise RuntimeError("build manifest reader accepted a corrupt sidecar")
