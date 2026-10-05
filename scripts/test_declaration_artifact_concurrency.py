"""Concurrent publication checks for P-04 declaration artifact storage."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

sys.path.insert(0, str(Path(__file__).resolve().parent))
import declaration_artifact_identity as identity


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


with tempfile.TemporaryDirectory(prefix="elisa-artifact-concurrent-") as temporary:
    root = Path(temporary)
    binary = root / "elisa-proof"
    binary.write_bytes(b"proof executable")
    manifest = {
        "schema": identity.MANIFEST_SCHEMA,
        "proof": {"source_tree_sha256": digest(b"proof sources")},
        "frontend": {"revision": "frontend-revision", "tree": digest(b"frontend tree")},
        "compiler": {"product": {"sha256": digest(b"compiler product")}},
        "runtime": {"sha256": digest(b"runtime")},
        "target": "arm64-apple-darwin",
        "compile_mode": "strict",
        "binary": {"sha256": digest(binary.read_bytes()), "path": str(binary)},
    }
    source = b"def concurrent(x): return x + 1\n"
    payload = b'{"status":"proved","certificates":[]}'
    dependencies = [{"kind": "type", "schema": "type-v1", "identity": "i64"}]
    record = identity.artifact_record(manifest, "src/concurrent.elisa", "function", "concurrent",
                                      source, payload, dependencies)
    store = root / "store"

    # Hold every publisher immediately before the atomic hard link so they compete for the
    # same absent content-addressed path at once. One link wins; the others must validate and
    # accept that complete immutable entry.
    publishers = 8
    link_barrier = Barrier(publishers)
    original_link = identity.os.link

    def synchronized_link(source_path: str, destination_path: str) -> None:
        link_barrier.wait(timeout=10)
        original_link(source_path, destination_path)

    identity.os.link = synchronized_link
    try:
        with ThreadPoolExecutor(max_workers=publishers) as pool:
            futures = [pool.submit(identity.publish_artifact, store, record, manifest,
                                   source, payload, dependencies)
                       for _ in range(publishers)]
            paths = [future.result(timeout=20) for future in futures]
    finally:
        identity.os.link = original_link

    expected_path = store / f"{record['artifact_sha256']}.json"
    assert paths == [expected_path] * publishers
    assert list(store.glob("*.json")) == [expected_path]
    assert not list(store.glob("*.tmp"))
    assert identity.read_artifact(store, record["artifact_sha256"], manifest,
                                  source, dependencies) == (record, payload)
