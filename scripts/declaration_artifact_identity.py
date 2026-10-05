#!/usr/bin/env python3
"""Canonical identities for compiler-bound per-declaration proof artifacts.

Version 1 deliberately uses the exact declaration source slice as its semantic input. It is
stable across line shifts and unrelated declarations, while formatting or comment edits inside
the declaration conservatively invalidate it. A future compiler frontend artifact can replace
that source slice with canonical resolved/typed declaration bytes under a new schema.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile


SCHEMA = "elisa-proof-declaration-artifact-v2"
MANIFEST_SCHEMA = "elisa-proof-build-manifest-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STORE_SCHEMA = "elisa-proof-declaration-artifact-store-v1"
MAX_RECORD_BYTES = 1024 * 1024
MAX_PAYLOAD_BYTES = 64 * 1024 * 1024
MAX_SOURCE_SLICE_BYTES = 512 * 1024
MAX_STORE_FILE_BYTES = MAX_RECORD_BYTES + 4 * ((MAX_PAYLOAD_BYTES + 2) // 3) + 4096


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def checked_manifest(path: Path) -> dict:
    """Load the current build manifest and check its checksum and named compiler output."""
    raw = path.read_bytes()
    checksum_path = Path(str(path) + ".sha256")
    expected = checksum_path.read_text(encoding="ascii").strip()
    if not is_sha256(expected) or sha256_bytes(raw) != expected:
        raise ValueError("build manifest checksum is missing or invalid")
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("build manifest is not valid JSON") from error
    if not isinstance(manifest, dict) or manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("unsupported proof build manifest schema")
    binary = manifest.get("binary")
    if not isinstance(binary, dict) or not is_sha256(binary.get("sha256")):
        raise ValueError("build manifest has no binary digest")
    binary_path = binary.get("path")
    if not isinstance(binary_path, str) or not binary_path:
        raise ValueError("build manifest has no binary path")
    required = (
        ("proof", "source_tree_sha256"),
        ("frontend", "revision"),
        ("frontend", "tree"),
        ("compiler", "product"),
        ("runtime", "sha256"),
    )
    for section, key in required:
        value = manifest.get(section)
        if not isinstance(value, dict) or not value.get(key):
            raise ValueError(f"build manifest is missing {section}.{key}")
    if not isinstance(manifest["frontend"]["revision"], str) or not isinstance(manifest["target"], str) \
            or not isinstance(manifest["compile_mode"], str):
        raise ValueError("build manifest has malformed frontend, target, or compile-mode identity")
    if not isinstance(manifest["compiler"]["product"], dict):
        raise ValueError("build manifest compiler product is malformed")
    if not isinstance(manifest["runtime"], dict):
        raise ValueError("build manifest runtime identity is malformed")
    if not is_sha256(manifest["proof"]["source_tree_sha256"]):
        raise ValueError("build manifest proof source digest is invalid")
    if not is_sha256(manifest["frontend"]["tree"]):
        raise ValueError("build manifest frontend tree digest is invalid")
    if not is_sha256(manifest["compiler"]["product"].get("sha256")):
        raise ValueError("build manifest compiler product digest is invalid")
    if not is_sha256(manifest["runtime"].get("sha256")):
        raise ValueError("build manifest runtime digest is invalid")
    try:
        actual_binary = sha256_bytes(Path(binary_path).read_bytes())
    except OSError as error:
        raise ValueError("proof executable named by the build manifest is unavailable") from error
    if actual_binary != binary["sha256"]:
        raise ValueError("proof executable does not match the build manifest")
    for key in ("target", "compile_mode"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise ValueError(f"build manifest is missing {key}")
    return manifest


def frontend_context(manifest: dict) -> dict:
    """Select the compiler/checker/ABI values that can change proof artifact meaning."""
    if not isinstance(manifest, dict) or manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("unsupported proof build manifest schema")
    proof = manifest.get("proof")
    frontend = manifest.get("frontend")
    compiler = manifest.get("compiler")
    runtime = manifest.get("runtime")
    binary = manifest.get("binary")
    if not all(isinstance(value, dict) for value in (proof, frontend, compiler, runtime, binary)):
        raise ValueError("proof build manifest context sections are malformed")
    product = compiler.get("product")
    if not isinstance(product, dict):
        raise ValueError("proof build manifest compiler product is malformed")
    if not isinstance(binary.get("path"), str) or not binary["path"]:
        raise ValueError("proof build manifest binary path is missing")
    if not isinstance(frontend.get("revision"), str) or not frontend["revision"]:
        raise ValueError("proof build manifest frontend revision is missing")
    if not is_sha256(frontend.get("tree")) or not is_sha256(proof.get("source_tree_sha256")) \
            or not is_sha256(product.get("sha256")) or not is_sha256(runtime.get("sha256")) \
            or not is_sha256(binary.get("sha256")):
        raise ValueError("proof build manifest context digest is malformed")
    if not isinstance(manifest.get("target"), str) or not manifest["target"] \
            or not isinstance(manifest.get("compile_mode"), str) or not manifest["compile_mode"]:
        raise ValueError("proof build manifest target or compile mode is missing")
    return {
        "manifest_schema": manifest["schema"],
        "frontend_revision": manifest["frontend"]["revision"],
        "frontend_tree_sha256": manifest["frontend"]["tree"],
        "compiler_product_sha256": manifest["compiler"]["product"]["sha256"],
        "proof_source_tree_sha256": manifest["proof"]["source_tree_sha256"],
        "proof_executable_sha256": manifest["binary"]["sha256"],
        "runtime_sha256": manifest["runtime"]["sha256"],
        "target": manifest["target"],
        "compile_mode": manifest["compile_mode"],
    }


def declaration_key(module: str, kind: str, name: str, source_slice: bytes) -> str:
    """Return a source-stable ID; `module` is a normalized project-relative path."""
    if not module or module.startswith("/") or "\\" in module or any(part in ("", ".", "..") for part in module.split("/")):
        raise ValueError("module identity must be a normalized relative path")
    if not kind or not name:
        raise ValueError("declaration kind and name are required")
    identity = {
        "schema": "elisa-declaration-source-identity-v1",
        "module": module,
        "kind": kind,
        "name": name,
        "source_slice_sha256": sha256_bytes(source_slice),
    }
    return sha256_bytes(canonical_bytes(identity))


def artifact_record(manifest: dict, module: str, kind: str, name: str,
                    source_slice: bytes, payload: bytes, dependencies: list[dict]) -> dict:
    """Build a canonical, integrity-checkable declaration artifact envelope.

    Dependencies are exact versioned identities supplied by the declaration graph producer.
    Their order is preserved to avoid silently normalizing a future order-sensitive format.
    """
    if not isinstance(source_slice, bytes) or len(source_slice) > MAX_SOURCE_SLICE_BYTES:
        raise ValueError("declaration source slice has an invalid type or exceeds the size limit")
    if not isinstance(dependencies, list):
        raise ValueError("dependencies must be an array")
    for dependency in dependencies:
        if not isinstance(dependency, dict) or not isinstance(dependency.get("identity"), str) \
                or not dependency["identity"] or not isinstance(dependency.get("kind"), str) \
                or not dependency["kind"] or not isinstance(dependency.get("schema"), str) \
                or not dependency["schema"]:
            raise ValueError("each dependency requires kind, schema, and identity")
    record = {
        "schema": SCHEMA,
        "context": frontend_context(manifest),
        "declaration": {
            "key": declaration_key(module, kind, name, source_slice),
            "module": module,
            "kind": kind,
            "name": name,
            "source_slice_sha256": sha256_bytes(source_slice),
            "source_slice_base64": base64.b64encode(source_slice).decode("ascii"),
        },
        "dependencies": dependencies,
        "payload_sha256": sha256_bytes(payload),
    }
    record["artifact_sha256"] = sha256_bytes(canonical_bytes(record))
    return record


def validate_record(record: dict, current_manifest: dict) -> bool:
    """Fail closed on schema, context, dependency shape, or envelope corruption."""
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        return False
    expected = record.get("artifact_sha256")
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        return False
    unhashed = {key: value for key, value in record.items() if key != "artifact_sha256"}
    try:
        actual = sha256_bytes(canonical_bytes(unhashed))
    except (TypeError, ValueError):
        return False
    if actual != expected:
        return False
    try:
        if record.get("context") != frontend_context(current_manifest):
            return False
        declaration = record["declaration"]
        if not SHA256_RE.fullmatch(declaration.get("key", "")):
            return False
        if not SHA256_RE.fullmatch(declaration.get("source_slice_sha256", "")):
            return False
        encoded_source = declaration.get("source_slice_base64")
        if not isinstance(encoded_source, str):
            return False
        source_bytes = base64.b64decode(encoded_source, validate=True)
        if len(source_bytes) > MAX_SOURCE_SLICE_BYTES \
                or base64.b64encode(source_bytes).decode("ascii") != encoded_source \
                or sha256_bytes(source_bytes) != declaration["source_slice_sha256"]:
            return False
        if not SHA256_RE.fullmatch(record.get("payload_sha256", "")):
            return False
    except (AttributeError, KeyError, TypeError, ValueError):
        return False
    if not isinstance(declaration, dict):
        return False
    dependencies = record.get("dependencies")
    if not isinstance(dependencies, list):
        return False
    if not all(isinstance(dep, dict) and isinstance(dep.get("kind"), str) and dep["kind"]
               and isinstance(dep.get("schema"), str) and dep["schema"]
               and isinstance(dep.get("identity"), str) and dep["identity"]
               for dep in dependencies):
        return False
    return all(isinstance(declaration.get(field), str) and declaration[field]
               for field in ("module", "kind", "name"))


def validate_record_for_source(record: dict, current_manifest: dict, source_slice: bytes) -> bool:
    if not validate_record(record, current_manifest):
        return False
    declaration = record["declaration"]
    if not isinstance(source_slice, bytes) or len(source_slice) > MAX_SOURCE_SLICE_BYTES:
        return False
    if declaration.get("source_slice_base64") != base64.b64encode(source_slice).decode("ascii") \
            or declaration.get("source_slice_sha256") != sha256_bytes(source_slice):
        return False
    try:
        return declaration.get("key") == declaration_key(
            declaration["module"], declaration["kind"], declaration["name"], source_slice
        )
    except (KeyError, TypeError, ValueError):
        return False


def validate_artifact_record(record: dict, current_manifest: dict,
                             source_slice: bytes, payload: bytes,
                             current_dependencies: list[dict]) -> bool:
    return validate_record_for_source(record, current_manifest, source_slice) \
        and record.get("payload_sha256") == sha256_bytes(payload) \
        and record.get("dependencies") == current_dependencies


def _store_path(store_dir: Path, artifact_sha256: str) -> Path:
    if not is_sha256(artifact_sha256):
        raise ValueError("artifact identity must be a lowercase SHA-256 digest")
    return store_dir / f"{artifact_sha256}.json"


def _encode_store_entry(record: dict, payload: bytes) -> bytes:
    record_bytes = canonical_bytes(record)
    if len(record_bytes) > MAX_RECORD_BYTES:
        raise ValueError("declaration artifact record exceeds the store size limit")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("declaration artifact payload exceeds the store size limit")
    envelope = {
        "schema": STORE_SCHEMA,
        "record": record,
        "payload_base64": base64.b64encode(payload).decode("ascii"),
    }
    encoded = canonical_bytes(envelope)
    if len(encoded) > MAX_STORE_FILE_BYTES:
        raise ValueError("declaration artifact entry exceeds the store size limit")
    return encoded


def publish_artifact(store_dir: Path, record: dict, current_manifest: dict,
                     source_slice: bytes, payload: bytes,
                     current_dependencies: list[dict]) -> Path:
    """Atomically publish a verified immutable artifact, returning its content-addressed path.

    A single bounded JSON file holds both the integrity envelope and payload. The temporary
    file is fsynced and hard-linked into place, so readers see either no entry or a complete
    entry and an existing artifact can never be overwritten.
    """
    if not isinstance(payload, bytes) or not isinstance(source_slice, bytes):
        raise ValueError("source slice and payload must be bytes")
    if not validate_artifact_record(record, current_manifest, source_slice, payload,
                                    current_dependencies):
        raise ValueError("declaration artifact identity validation failed")
    entry = _encode_store_entry(record, payload)
    destination = _store_path(Path(store_dir), record["artifact_sha256"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".artifact-", suffix=".tmp",
                                                   dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(entry)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            # Idempotent publication is allowed only when the existing complete entry verifies.
            old_record, old_payload = read_artifact(
                destination.parent, record["artifact_sha256"], current_manifest,
                source_slice, current_dependencies
            )
            if old_record != record or old_payload != payload:
                raise ValueError("immutable declaration artifact path contains different data")
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return destination


def read_artifact(store_dir: Path, artifact_sha256: str, current_manifest: dict,
                  source_slice: bytes, current_dependencies: list[dict]) -> tuple[dict, bytes]:
    """Read a bounded store entry and reject every incomplete or stale identity."""
    if not isinstance(source_slice, bytes) or not isinstance(current_dependencies, list):
        raise ValueError("current source slice and dependencies have invalid types")
    path = _store_path(Path(store_dir), artifact_sha256)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError("declaration artifact entry is missing or unavailable") from error
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size < 1 \
                or file_stat.st_size > MAX_STORE_FILE_BYTES:
            raise ValueError("declaration artifact entry has an invalid size or file type")
        with os.fdopen(descriptor, "rb", closefd=False) as source:
            raw = source.read(MAX_STORE_FILE_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(raw) != file_stat.st_size or len(raw) > MAX_STORE_FILE_BYTES:
        raise ValueError("declaration artifact entry is truncated or oversized")
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("declaration artifact entry is not valid JSON") from error
    if not isinstance(envelope, dict) or envelope.get("schema") != STORE_SCHEMA:
        raise ValueError("unsupported declaration artifact store schema")
    record = envelope.get("record")
    encoded_payload = envelope.get("payload_base64")
    if not isinstance(record, dict) or not isinstance(encoded_payload, str):
        raise ValueError("declaration artifact entry is incomplete")
    if len(canonical_bytes(record)) > MAX_RECORD_BYTES:
        raise ValueError("declaration artifact record exceeds the store size limit")
    try:
        payload = base64.b64decode(encoded_payload, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("declaration artifact payload encoding is invalid") from error
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("declaration artifact payload exceeds the store size limit")
    if record.get("artifact_sha256") != artifact_sha256 or not validate_artifact_record(
            record, current_manifest, source_slice, payload, current_dependencies):
        raise ValueError("declaration artifact identities do not match current inputs")
    return record, payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--kind", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--source-slice", type=Path, required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True,
                        help="JSON array of {kind, schema, identity} records")
    arguments = parser.parse_args()
    try:
        manifest = checked_manifest(arguments.manifest)
        dependencies = json.loads(arguments.dependencies.read_text(encoding="utf-8"))
        if not isinstance(dependencies, list):
            raise ValueError("dependencies file must contain a JSON array")
        record = artifact_record(manifest, arguments.module, arguments.kind, arguments.name,
                                 arguments.source_slice.read_bytes(), arguments.payload.read_bytes(), dependencies)
        sys.stdout.buffer.write(canonical_bytes(record) + b"\n")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"declaration artifact identity: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
