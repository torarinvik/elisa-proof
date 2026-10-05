"""Remote cross-builds must publish both linked products as one generation."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "scripts/remote/build.sh"
PUBLISHER = ROOT / "scripts/verify_product_pair.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    script = BUILD.read_text()
    assert '--new-pair-generation' in script
    assert '--pair-generation "$generation"' in script
    assert 'for product in elisa-proof elisa-proof-replay; do' in script
    assert '--proof-binary "$stage/elisa-proof"' in script
    assert '--proof-manifest "$stage/elisa-proof.manifest.json"' in script
    assert '--replay-binary "$stage/elisa-proof-replay"' in script
    assert '--replay-manifest "$stage/elisa-proof-replay.manifest.json"' in script
    assert 'resolve --generation-root build/elisa-proof-generations' in script

    generation = "a" * 32
    source_identity = {
        "head": "fixture-source-head",
        "source_dirty": False,
        "source_tree_sha256": "fixture-source-tree",
    }
    with tempfile.TemporaryDirectory(prefix="remote-pair-regression-") as temporary:
        root = Path(temporary)
        binaries = [root / "elisa-proof", root / "elisa-proof-replay"]
        manifests = [root / f"{binary.name}.manifest.json" for binary in binaries]
        for index, (binary, manifest) in enumerate(zip(binaries, manifests)):
            binary.write_bytes(f"linked product {index}\n".encode())
            payload = {
                "schema": "elisa-proof-build-manifest-v1",
                "pair_generation": generation,
                "proof": source_identity,
                "binary": {"sha256": sha256(binary)},
            }
            encoded = json.dumps(payload, sort_keys=True).encode() + b"\n"
            manifest.write_bytes(encoded)
            manifest.with_name(manifest.name + ".sha256").write_text(
                hashlib.sha256(encoded).hexdigest() + "\n", encoding="ascii"
            )

        subprocess.run(
            [
                sys.executable,
                str(PUBLISHER),
                "publish",
                "--generation-root",
                str(root / "generations"),
                "--generation",
                generation,
                "--proof-binary",
                str(binaries[0]),
                "--proof-manifest",
                str(manifests[0]),
                "--replay-binary",
                str(binaries[1]),
                "--replay-manifest",
                str(manifests[1]),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        resolved = subprocess.run(
            [
                sys.executable,
                str(PUBLISHER),
                "resolve",
                "--generation-root",
                str(root / "generations"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        pair = json.loads(resolved.stdout)
        assert pair["pair_generation"] == generation
        products = pair["products"]
        assert Path(products["elisa-proof"]["binary"]).parent == Path(
            products["elisa-proof-replay"]["binary"]
        ).parent
        assert products["elisa-proof"]["binary_sha256"] == sha256(
            Path(products["elisa-proof"]["binary"])
        )
        assert products["elisa-proof-replay"]["binary_sha256"] == sha256(
            Path(products["elisa-proof-replay"]["binary"])
        )

    print("remote build pair publication: proof and replay resolve from one generation")


if __name__ == "__main__":
    main()
