"""A stale manifest checksum must invalidate an otherwise matching build record."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_TOOL = ROOT / "scripts/build_manifest.py"


def check(binary: Path, manifest: Path, checksum: Path) -> int:
    result = subprocess.run(
        ["python3", str(MANIFEST_TOOL), "--check-existing",
         "--recorded-build-identity", "fixture-identity",
         "--existing-binary", str(binary),
         "--existing-manifest", str(manifest),
         "--existing-manifest-sha256", str(checksum)],
        check=False,
    )
    return result.returncode


with tempfile.TemporaryDirectory(prefix="elisa-manifest-sidecar-") as directory:
    root = Path(directory)
    binary = root / "proof-bin"
    manifest = root / "proof-bin.manifest.json"
    checksum = root / "proof-bin.manifest.json.sha256"
    binary_bytes = b"fixture binary"
    binary.write_bytes(binary_bytes)
    manifest_bytes = json.dumps({
        "build_identity": "fixture-identity",
        "binary": {"sha256": hashlib.sha256(binary_bytes).hexdigest()},
    }, sort_keys=True).encode() + b"\n"
    manifest.write_bytes(manifest_bytes)
    valid_digest = hashlib.sha256(manifest_bytes).hexdigest()
    checksum.write_text(valid_digest + "\n", encoding="ascii")

    assert check(binary, manifest, checksum) == 0
    checksum.write_text("0" * 64 + "\n", encoding="ascii")
    assert check(binary, manifest, checksum) == 1, "tampered manifest checksum must force a cache miss"
    checksum.write_text(valid_digest + "\n", encoding="ascii")
    assert check(binary, manifest, checksum) == 0

print("build manifest: a corrupted checksum sidecar invalidates an otherwise matching product")
