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
import shutil
import sys
import tempfile


PRODUCTS = ("elisa-proof", "elisa-proof-replay")


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
    recorded_manifest_digest = checksum_path.read_text(encoding="ascii").strip()
    if recorded_manifest_digest != hashlib.sha256(raw).hexdigest():
        raise ValueError(f"manifest checksum mismatch: {manifest_path}")
    if manifest.get("pair_generation") != generation:
        raise ValueError(f"generation mismatch in {manifest_path}")
    actual_binary_digest = sha256(binary)
    if manifest.get("binary", {}).get("sha256") != actual_binary_digest:
        raise ValueError(f"binary checksum mismatch: {binary}")
    return manifest


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
    arguments = parser.parse_args()
    try:
        return publish(arguments) if arguments.command == "publish" else resolve(arguments)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as error:
        print(f"product pair: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
