"""Focused identity and fail-closed checks for P-04 declaration artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import declaration_artifact_identity as identity


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reseal(record: dict) -> dict:
    record.pop("artifact_sha256", None)
    record["artifact_sha256"] = digest(identity.canonical_bytes(record))
    return record


def manifest_fixture(directory: Path) -> dict:
    binary = directory / "elisa-proof"
    binary.write_bytes(b"proof executable")
    return {
        "schema": identity.MANIFEST_SCHEMA,
        "proof": {"source_tree_sha256": digest(b"proof sources")},
        "frontend": {"revision": "frontend-revision", "tree": digest(b"frontend tree")},
        "compiler": {"product": {"sha256": digest(b"compiler product")}},
        "runtime": {"sha256": digest(b"runtime")},
        "target": "arm64-apple-darwin",
        "compile_mode": "strict",
        "binary": {"sha256": digest(binary.read_bytes()), "path": str(binary)},
    }


with tempfile.TemporaryDirectory(prefix="elisa-declaration-identity-") as temporary:
    root = Path(temporary)
    manifest = manifest_fixture(root)
    manifest_path = root / "proof.manifest.json"
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    Path(str(manifest_path) + ".sha256").write_text(digest(manifest_bytes) + "\n", encoding="ascii")
    assert identity.checked_manifest(manifest_path) == manifest
    declaration_source = b"def calculate(x: i64) -> i64:\n    return x + 1\n"
    payload = b'{"status":"proved","certificates":[]}'
    dependencies = [
        {"kind": "callee-summary", "schema": "elisa-proof-declaration-artifact-v1", "identity": "callee-id-v1"},
        {"kind": "resolved-type", "schema": "elisa-frontend-type-v1", "identity": "type-id-v1"},
    ]
    record = identity.artifact_record(manifest, "src/math.elisa", "function", "Math::calculate",
                                     declaration_source, payload, dependencies)

    # Line movement outside the exact declaration slice and unrelated declarations do not alter
    # this source identity; a body change does.
    shifted = identity.artifact_record(manifest, "src/math.elisa", "function", "Math::calculate",
                                       declaration_source, payload, dependencies)
    assert shifted["declaration"]["key"] == record["declaration"]["key"]
    assert identity.validate_artifact_record(record, manifest, declaration_source, payload, dependencies)
    assert not identity.validate_record_for_source(record, manifest, declaration_source + b"\n")
    assert not identity.validate_artifact_record(record, manifest, declaration_source, payload + b" ", dependencies)
    assert not identity.validate_artifact_record(record, manifest, declaration_source, payload, dependencies[::-1])
    changed_dependencies = [dict(dependency) for dependency in dependencies]
    changed_dependencies[0]["identity"] = "changed-callee-id"
    assert not identity.validate_artifact_record(record, manifest, declaration_source, payload,
                                                 changed_dependencies)

    # Store entries publish atomically as immutable, bounded envelopes and verify every identity
    # again when read. A failed link leaves no visible partial artifact.
    store = root / "artifact-store"
    stored_path = identity.publish_artifact(store, record, manifest, declaration_source,
                                            payload, dependencies)
    assert stored_path == store / f"{record['artifact_sha256']}.json"
    assert identity.read_artifact(store, record["artifact_sha256"], manifest,
                                  declaration_source, dependencies) == (record, payload)
    assert identity.publish_artifact(store, record, manifest, declaration_source,
                                     payload, dependencies) == stored_path
    try:
        identity.read_artifact(store, "0" * 64, manifest, declaration_source, dependencies)
    except ValueError as error:
        assert "missing" in str(error)
    else:
        raise AssertionError("missing declaration artifact was accepted")
    try:
        identity.read_artifact(store, record["artifact_sha256"], manifest,
                               declaration_source, changed_dependencies)
    except ValueError as error:
        assert "identities" in str(error)
    else:
        raise AssertionError("artifact with stale dependency identities was accepted")
    try:
        identity.read_artifact(store, record["artifact_sha256"], manifest,
                               declaration_source + b"# changed", dependencies)
    except ValueError as error:
        assert "identities" in str(error)
    else:
        raise AssertionError("artifact for a stale source slice was accepted")

    # Even a deliberately colliding digest backend cannot make a different source slice
    # indistinguishable at admission or at a content-addressed store path.
    collision_store = root / "collision-store"
    source_one = b"def collision_a(): pass\n"
    source_two = b"def collision_b(): pass\n"
    original_digest = identity.sha256_bytes
    forced_digest = "a" * 64

    def colliding_digest(data: bytes) -> str:
        if data in (source_one, source_two):
            return forced_digest
        try:
            value = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError):
            value = None
        if isinstance(value, dict) and isinstance(value.get("declaration"), dict) \
                and "source_slice_base64" in value["declaration"]:
            return forced_digest
        return original_digest(data)

    identity.sha256_bytes = colliding_digest
    try:
        collision_one = identity.artifact_record(manifest, "src/collision.elisa", "function", "f",
                                                 source_one, payload, dependencies)
        collision_two = identity.artifact_record(manifest, "src/collision.elisa", "function", "f",
                                                 source_two, payload, dependencies)
        assert collision_one["declaration"]["key"] == collision_two["declaration"]["key"]
        assert collision_one["artifact_sha256"] == collision_two["artifact_sha256"]
        collision_path = identity.publish_artifact(collision_store, collision_one, manifest,
                                                   source_one, payload, dependencies)
        first_entry = collision_path.read_bytes()
        for operation in (
            lambda: identity.publish_artifact(collision_store, collision_two, manifest,
                                              source_two, payload, dependencies),
            lambda: identity.read_artifact(collision_store, collision_two["artifact_sha256"],
                                           manifest, source_two, dependencies),
        ):
            try:
                operation()
            except ValueError as error:
                assert "identity" in str(error) or "identities" in str(error)
            else:
                raise AssertionError("colliding source digest bypassed artifact admission")
        assert collision_path.read_bytes() == first_entry
        assert identity.read_artifact(collision_store, collision_one["artifact_sha256"],
                                      manifest, source_one, dependencies) == (collision_one, payload)
    finally:
        identity.sha256_bytes = original_digest

    oversized_store = root / "oversized-store"
    oversized_store.mkdir()
    oversized_path = oversized_store / f"{record['artifact_sha256']}.json"
    with oversized_path.open("wb") as output:
        output.truncate(identity.MAX_STORE_FILE_BYTES + 1)
    try:
        identity.read_artifact(oversized_store, record["artifact_sha256"], manifest,
                               declaration_source, dependencies)
    except ValueError as error:
        assert "size" in str(error)
    else:
        raise AssertionError("oversized declaration artifact was read")

    interrupted_store = root / "interrupted-store"
    original_link = identity.os.link
    def fail_link(source: str, destination: str) -> None:
        raise OSError("simulated interruption before publication")
    identity.os.link = fail_link
    try:
        try:
            identity.publish_artifact(interrupted_store, record, manifest, declaration_source,
                                      payload, dependencies)
        except OSError as error:
            assert "simulated interruption" in str(error)
        else:
            raise AssertionError("simulated publication interruption was ignored")
    finally:
        identity.os.link = original_link
    assert not (interrupted_store / f"{record['artifact_sha256']}.json").exists()
    assert not list(interrupted_store.glob("*.tmp"))

    stored_path.write_bytes(b'{"schema":"elisa-proof-declaration-artifact-store-v1"')
    try:
        identity.read_artifact(store, record["artifact_sha256"], manifest,
                               declaration_source, dependencies)
    except ValueError as error:
        assert "JSON" in str(error)
    else:
        raise AssertionError("truncated declaration artifact was accepted")

    # The compiler C-04 frontend identity is bound through the canonical build manifest.
    changed_frontend = json.loads(json.dumps(manifest))
    changed_frontend["frontend"]["tree"] = digest(b"new frontend tree")
    assert not identity.validate_record_for_source(record, changed_frontend, declaration_source)
    changed_record = identity.artifact_record(changed_frontend, "src/math.elisa", "function",
                                              "Math::calculate", declaration_source, payload, dependencies)
    assert changed_record["artifact_sha256"] != record["artifact_sha256"]

    # A broken compiler manifest or a replaced product cannot provide artifact context.
    Path(str(manifest_path) + ".sha256").write_text("0" * 64 + "\n", encoding="ascii")
    try:
        identity.checked_manifest(manifest_path)
    except ValueError as error:
        assert "checksum" in str(error)
    else:
        raise AssertionError("invalid build-manifest checksum was accepted")

    missing_path = json.loads(manifest_bytes)
    missing_path["binary"].pop("path")
    missing_path_bytes = json.dumps(missing_path, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_path.write_bytes(missing_path_bytes)
    Path(str(manifest_path) + ".sha256").write_text(digest(missing_path_bytes) + "\n", encoding="ascii")
    try:
        identity.checked_manifest(manifest_path)
    except ValueError as error:
        assert "binary path" in str(error)
    else:
        raise AssertionError("build manifest without executable path was accepted")

    # Corrupt payload metadata and unsupported schema versions fail closed.
    corrupt = json.loads(json.dumps(record))
    corrupt["payload_sha256"] = digest(b"different payload")
    assert not identity.validate_record_for_source(corrupt, manifest, declaration_source)
    unsupported = json.loads(json.dumps(record))
    unsupported["schema"] = "elisa-proof-declaration-artifact-v3"
    assert not identity.validate_record_for_source(unsupported, manifest, declaration_source)
    malformed_records = []
    malformed_declaration = json.loads(json.dumps(record))
    malformed_declaration["declaration"] = []
    malformed_records.append(malformed_declaration)
    malformed_dependencies = json.loads(json.dumps(record))
    malformed_dependencies["dependencies"] = {"missing": "array"}
    malformed_records.append(malformed_dependencies)
    malformed_dependency_item = json.loads(json.dumps(record))
    malformed_dependency_item["dependencies"][0] = []
    malformed_records.append(malformed_dependency_item)
    for malformed in malformed_records:
        assert not identity.validate_record(reseal(malformed), manifest)
    assert not identity.validate_record_for_source(record, {"frontend": []}, declaration_source)
    no_binary_path = json.loads(json.dumps(manifest))
    no_binary_path["binary"].pop("path")
    assert not identity.validate_record(record, no_binary_path)

    # Stable module/declaration identity must be explicit and traversal-free.
    try:
        identity.declaration_key("../outside.elisa", "function", "f", declaration_source)
    except ValueError:
        pass
    else:
        raise AssertionError("path traversal in module identity was accepted")
