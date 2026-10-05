#!/usr/bin/env python3
"""Publish and resolve immutable proof/replay product generations.

Consumers must call ``resolve`` once and execute the returned generation paths. They must not
independently open the legacy build/elisa-proof* names. Generations are retained (no GC), so a
resolved path remains available across later pointer changes. Hashes are checked when resolving;
this is integrity checking, not protection against a hostile writer that can replace the files.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


PRODUCTS = ("elisa-proof", "elisa-proof-replay")
BUILD_IDENTITY_FIELDS = (
    "frontend",
    "compiler",
    "runtime",
    "profile_hooks",
    "target",
    "optimization",
    "compile_mode",
    "compiler_flags",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read_manifest(binary: Path, generation: str) -> dict:
    manifest_path = binary.with_name(binary.name + ".manifest.json")
    checksum_path = manifest_path.with_name(manifest_path.name + ".sha256")
    for artifact in (binary, manifest_path, checksum_path):
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError(f"generation artifact is not a regular file: {artifact}")
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if not isinstance(manifest, dict):
        raise ValueError(f"manifest root is not an object: {manifest_path}")
    recorded_manifest_digest = checksum_path.read_text(encoding="ascii").strip()
    if recorded_manifest_digest != hashlib.sha256(raw).hexdigest():
        raise ValueError(f"manifest checksum mismatch: {manifest_path}")
    if manifest.get("pair_generation") != generation:
        raise ValueError(f"generation mismatch in {manifest_path}")
    actual_binary_digest = sha256(binary)
    binary_identity = manifest.get("binary")
    if not isinstance(binary_identity, dict) or binary_identity.get("sha256") != actual_binary_digest:
        raise ValueError(f"binary checksum mismatch: {binary}")
    return manifest


def shared_build_identity(manifest: dict) -> dict:
    """Return the build inputs that must be identical for both executable roles.

    Per-product binary hashes and build_identity values are intentionally excluded: each
    executable has a different entry point and dependency closure. Their shared toolchain,
    frontend, runtime, target, and compilation policy are not product-specific.
    """
    missing = [field for field in BUILD_IDENTITY_FIELDS if field not in manifest]
    if missing:
        raise ValueError(f"build manifest is missing shared identity fields: {', '.join(missing)}")
    if manifest.get("schema") != "elisa-proof-build-manifest-v1":
        raise ValueError("build manifest has an unsupported schema")

    frontend = manifest["frontend"]
    compiler = manifest["compiler"]
    runtime = manifest["runtime"]
    profile_hooks = manifest["profile_hooks"]
    if not isinstance(frontend, dict) or not isinstance(compiler, dict):
        raise ValueError("build manifest has malformed frontend/compiler identity")
    if not isinstance(runtime, dict) or not isinstance(profile_hooks, dict):
        raise ValueError("build manifest has malformed runtime/profile-hook identity")

    frontend_revision = frontend.get("revision")
    frontend_tree = frontend.get("tree")
    if not isinstance(frontend_revision, str) or not frontend_revision:
        raise ValueError("build manifest has no frontend revision")
    if not isinstance(frontend_tree, str) or re.fullmatch(r"[0-9a-f]{40}", frontend_tree) is None:
        raise ValueError("build manifest has no valid frontend tree identity")

    stage = compiler.get("stage")
    if stage not in ("stage0", "stage1"):
        raise ValueError("build manifest has an invalid compiler stage")
    compiler_identity = {
        "stage": stage,
        "stage1_revision": compiler.get("stage1_revision"),
        "source_revision": compiler.get("source_revision"),
        "source_dirty": compiler.get("source_dirty"),
    }
    if any(field not in compiler for field in ("stage1_revision", "source_revision", "source_dirty")):
        raise ValueError("build manifest is missing compiler source provenance")
    if compiler_identity["stage1_revision"] is not None and not isinstance(compiler_identity["stage1_revision"], str):
        raise ValueError("build manifest has malformed Stage1 revision")
    if compiler_identity["source_revision"] is not None and not isinstance(compiler_identity["source_revision"], str):
        raise ValueError("build manifest has malformed compiler source revision")
    if compiler_identity["source_dirty"] is not None and not isinstance(compiler_identity["source_dirty"], bool):
        raise ValueError("build manifest has malformed compiler dirty-source flag")
    for role in ("executable", "product"):
        artifact = compiler.get(role)
        if not isinstance(artifact, dict):
            raise ValueError(f"build manifest has no compiler {role} identity")
        digest = artifact.get("sha256")
        size = artifact.get("bytes")
        if (not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or not isinstance(size, int) or isinstance(size, bool) or size <= 0):
            raise ValueError(f"build manifest has an invalid compiler {role} identity")
        compiler_identity[role] = {"sha256": digest, "bytes": size}

    def linked_artifact_identity(name: str, artifact: dict) -> dict:
        if "sha256" not in artifact:
            raise ValueError(f"build manifest is missing {name} digest")
        digest = artifact.get("sha256")
        size = artifact.get("bytes")
        if digest is None and size is None:
            if artifact.get("path") is not None:
                raise ValueError(f"build manifest has an incomplete {name} identity")
            return {"sha256": None, "bytes": None}
        if (not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or not isinstance(size, int) or isinstance(size, bool) or size <= 0):
            raise ValueError(f"build manifest has an invalid {name} identity")
        return {"sha256": digest, "bytes": size}

    if not isinstance(manifest["target"], str) or not manifest["target"]:
        raise ValueError("build manifest has no target identity")
    if not isinstance(manifest["optimization"], str) or not manifest["optimization"]:
        raise ValueError("build manifest has no optimization identity")
    if not isinstance(manifest["compile_mode"], str) or not manifest["compile_mode"]:
        raise ValueError("build manifest has no compile-mode identity")
    flags = manifest["compiler_flags"]
    if not isinstance(flags, list) or any(not isinstance(flag, str) for flag in flags):
        raise ValueError("build manifest has malformed compiler flags")

    return {
        "frontend": {"revision": frontend_revision, "tree": frontend_tree},
        "compiler": compiler_identity,
        "runtime": linked_artifact_identity("runtime", runtime),
        "profile_hooks": linked_artifact_identity("profile hooks", profile_hooks),
        "target": manifest["target"],
        "optimization": manifest["optimization"],
        "compile_mode": manifest["compile_mode"],
        "compiler_flags": flags,
    }


def require_matching_build_identity(proof: dict, replay: dict) -> None:
    if shared_build_identity(proof) != shared_build_identity(replay):
        raise ValueError("proof and replay manifests describe different toolchain/build identities")


def failpoint(name: str) -> None:
    if os.environ.get("ELISA_PROOF_PUBLISH_FAIL_AT") == name:
        raise RuntimeError(f"injected publication failure at {name}")


def publish(arguments: argparse.Namespace) -> int:
    root = Path(arguments.generation_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    generation = arguments.generation
    if not generation or any(c not in "0123456789abcdef" for c in generation):
        raise ValueError("generation must be a lowercase hexadecimal identity")
    sources = [Path(arguments.proof_binary), Path(arguments.replay_binary)]
    manifests = [Path(arguments.proof_manifest), Path(arguments.replay_manifest)]
    for manifest in manifests:
        parsed = json.loads(manifest.read_text(encoding="utf-8"))
        if parsed.get("pair_generation") != generation:
            raise ValueError(f"staged manifest has wrong pair_generation: {manifest}")
    staged_pair = [read_manifest(binary, generation) for binary in sources]
    if staged_pair[0].get("proof") != staged_pair[1].get("proof"):
        raise ValueError("proof and replay manifests describe different source snapshots")
    require_matching_build_identity(staged_pair[0], staged_pair[1])

    final = root / generation
    if final.exists():
        raise ValueError(f"generation already exists and is immutable: {final}")
    temporary = Path(tempfile.mkdtemp(prefix=f".{generation}.staging-", dir=root))
    try:
        for product, source, source_manifest in zip(PRODUCTS, sources, manifests):
            binary = temporary / product
            shutil.copyfile(source, binary)
            os.chmod(binary, 0o555)
            manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
            manifest["binary"]["path"] = str(final / product)
            encoded = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
            manifest_path = binary.with_name(binary.name + ".manifest.json")
            manifest_path.write_bytes(encoded)
            os.chmod(manifest_path, 0o444)
            checksum_path = manifest_path.with_name(manifest_path.name + ".sha256")
            checksum_path.write_text(hashlib.sha256(encoded).hexdigest() + "\n", encoding="ascii")
            os.chmod(checksum_path, 0o444)
        failpoint("before-generation-rename")
        for path in temporary.iterdir():
            with path.open("rb") as stream:
                os.fsync(stream.fileno())
        fsync_directory(temporary)
        os.replace(temporary, final)
        os.chmod(final, 0o555)
        fsync_directory(root)
        failpoint("after-generation-rename")

        pointer_temp = root / f".current-{generation}.tmp"
        pointer_temp.write_text(generation + "\n", encoding="ascii")
        with pointer_temp.open("rb") as stream:
            os.fsync(stream.fileno())
        failpoint("before-pointer-replace")
        os.replace(pointer_temp, root / "CURRENT")
        fsync_directory(root)
        failpoint("after-pointer-replace")
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    print(final)
    return 0


def resolve(arguments: argparse.Namespace) -> int:
    root = Path(arguments.generation_root).resolve()
    pointer = root / "CURRENT"
    generation = pointer.read_text(encoding="ascii").strip()
    if not generation or any(c not in "0123456789abcdef" for c in generation):
        raise ValueError("CURRENT does not contain a valid generation identity")
    directory = root / generation
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"current generation is missing or not a directory: {directory}")
    binaries = [directory / name for name in PRODUCTS]
    pair = [read_manifest(binary, generation) for binary in binaries]
    if pair[0].get("proof") != pair[1].get("proof"):
        raise ValueError("proof and replay products do not share source provenance")
    require_matching_build_identity(pair[0], pair[1])
    result = {
        "pair_generation": generation,
        "products": {
            name: {
                "binary": str(binary),
                "binary_sha256": pair[index]["binary"]["sha256"],
                "manifest": str(binary.with_name(binary.name + ".manifest.json")),
            }
            for index, (name, binary) in enumerate(zip(PRODUCTS, binaries))
        },
    }
    print(json.dumps(result, sort_keys=True))
    return 0


def read_compatibility_manifest(binary: Path, manifest_path: Path, checksum_path: Path) -> dict:
    for artifact in (binary, manifest_path, checksum_path):
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError(f"expected build artifact is not a regular file: {artifact}")
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if not isinstance(manifest, dict):
        raise ValueError(f"expected manifest root is not an object: {manifest_path}")
    if checksum_path.read_text(encoding="ascii").strip() != hashlib.sha256(raw).hexdigest():
        raise ValueError(f"expected manifest checksum mismatch: {manifest_path}")
    binary_identity = manifest.get("binary")
    if not isinstance(binary_identity, dict) or binary_identity.get("sha256") != sha256(binary):
        raise ValueError(f"expected binary checksum mismatch: {binary}")
    return manifest


def check_current(arguments: argparse.Namespace) -> int:
    """Return success only when CURRENT is the exact pair represented by build outputs."""
    expected = [
        read_compatibility_manifest(Path(arguments.proof_binary),
                                    Path(arguments.proof_manifest),
                                    Path(arguments.proof_manifest_sha256)),
        read_compatibility_manifest(Path(arguments.replay_binary),
                                    Path(arguments.replay_manifest),
                                    Path(arguments.replay_manifest_sha256)),
    ]
    if expected[0].get("proof") != expected[1].get("proof"):
        raise ValueError("expected proof and replay outputs have different source provenance")
    require_matching_build_identity(expected[0], expected[1])

    try:
        root = Path(arguments.generation_root).resolve()
        generation = (root / "CURRENT").read_text(encoding="ascii").strip()
        if not generation or any(character not in "0123456789abcdef" for character in generation):
            raise ValueError("CURRENT does not contain a valid generation identity")
        directory = root / generation
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError(f"current generation is missing or not a regular directory: {directory}")
        current = [read_manifest(directory / name, generation) for name in PRODUCTS]
        if current[0].get("proof") != expected[0].get("proof"):
            raise ValueError("current pair names a different proof source snapshot")
        require_matching_build_identity(current[0], current[1])
        for product, actual, wanted in zip(PRODUCTS, current, expected):
            if actual.get("build_identity") != wanted.get("build_identity"):
                raise ValueError(f"current {product} has a different build identity")
            if actual.get("binary", {}).get("sha256") != wanted.get("binary", {}).get("sha256"):
                raise ValueError(f"current {product} has a different executable")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"product pair: current generation requires refresh: {error}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    publish_parser = commands.add_parser("publish")
    publish_parser.add_argument("--generation-root", required=True)
    publish_parser.add_argument("--generation", required=True)
    publish_parser.add_argument("--proof-binary", required=True)
    publish_parser.add_argument("--proof-manifest", required=True)
    publish_parser.add_argument("--replay-binary", required=True)
    publish_parser.add_argument("--replay-manifest", required=True)
    resolve_parser = commands.add_parser("resolve")
    resolve_parser.add_argument("--generation-root", required=True)
    current_parser = commands.add_parser("check-current")
    current_parser.add_argument("--generation-root", required=True)
    current_parser.add_argument("--proof-binary", required=True)
    current_parser.add_argument("--proof-manifest", required=True)
    current_parser.add_argument("--proof-manifest-sha256", required=True)
    current_parser.add_argument("--replay-binary", required=True)
    current_parser.add_argument("--replay-manifest", required=True)
    current_parser.add_argument("--replay-manifest-sha256", required=True)
    arguments = parser.parse_args()
    try:
        if arguments.command == "publish":
            return publish(arguments)
        if arguments.command == "resolve":
            return resolve(arguments)
        return check_current(arguments)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as error:
        print(f"product pair: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
