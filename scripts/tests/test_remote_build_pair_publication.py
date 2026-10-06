"""Remote cross-builds must publish both linked products as one matching generation."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "scripts/remote/build.sh"
PUBLISHER = ROOT / "scripts/verify_product_pair.py"
GENERATION = "a" * 32

SOURCE_IDENTITY = {
    "head": "fixture-source-head",
    "source_dirty": False,
    "source_tree_sha256": "fixture-source-tree",
}

SHARED_IDENTITY = {
    "schema": "elisa-proof-build-manifest-v1",
    "frontend": {"revision": "a" * 40, "tree": "1" * 40},
    "compiler": {
        "stage": "stage1",
        "stage1_revision": "a" * 40,
        "source_revision": "a" * 40,
        "source_tree_sha256": "a" * 64,
        "build_recipe_sha256": "b" * 64,
        "source_dirty": False,
        "executable": {"path": "/toolchain/elisac-stage1", "sha256": "2" * 64, "bytes": 10},
        "product": {"path": "/toolchain/compiler-product", "sha256": "3" * 64, "bytes": 20},
    },
    "runtime": {"path": "/toolchain/runtime.o", "sha256": "4" * 64, "bytes": 30},
    "profile_hooks": {"path": "/toolchain/profile_hooks.o", "sha256": "5" * 64, "bytes": 40},
    "target": "arm64-fixture",
    "optimization": "O2",
    "compile_mode": "strict",
    "compiler_flags": ["-emit", "obj", "-O2"],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(path: Path, payload: dict) -> None:
    encoded = (json.dumps(payload, sort_keys=True) + "\n").encode()
    path.write_bytes(encoded)
    path.with_name(path.name + ".sha256").write_text(
        hashlib.sha256(encoded).hexdigest() + "\n", encoding="ascii"
    )


def create_staged_pair(directory: Path, mutation=None) -> tuple[list[Path], list[Path]]:
    directory.mkdir(parents=True, exist_ok=True)
    binaries = [directory / "elisa-proof", directory / "elisa-proof-replay"]
    manifests = [directory / f"{binary.name}.manifest.json" for binary in binaries]
    for index, (binary, manifest_path) in enumerate(zip(binaries, manifests)):
        binary.write_bytes(f"linked product {index}\n".encode())
        payload = copy.deepcopy(SHARED_IDENTITY)
        payload.update(
            pair_generation=GENERATION,
            proof=copy.deepcopy(SOURCE_IDENTITY),
            # These are per-product cache/build keys and may differ by entry point.
            build_identity=f"product-specific-identity-{index}",
            binary={"sha256": sha256(binary), "path": str(binary)},
        )
        if index == 1 and mutation is not None:
            mutation(payload)
        write_manifest(manifest_path, payload)
    return binaries, manifests


def command(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PUBLISHER), *arguments],
        capture_output=True,
        text=True,
    )


def publish(root: Path, binaries: list[Path], manifests: list[Path]) -> subprocess.CompletedProcess:
    return command(
        "publish",
        "--generation-root", str(root),
        "--generation", GENERATION,
        "--proof-binary", str(binaries[0]),
        "--proof-manifest", str(manifests[0]),
        "--replay-binary", str(binaries[1]),
        "--replay-manifest", str(manifests[1]),
    )


def assert_rejected(result: subprocess.CompletedProcess, expected: str) -> None:
    assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
    assert expected in result.stderr, result.stderr


def main() -> None:
    script = BUILD.read_text()
    assert "--new-pair-generation" in script
    assert '--pair-generation "$generation"' in script
    assert "for product in elisa-proof elisa-proof-replay; do" in script
    assert '--proof-binary "$stage/elisa-proof"' in script
    assert '--proof-manifest "$stage/elisa-proof.manifest.json"' in script
    assert '--replay-binary "$stage/elisa-proof-replay"' in script
    assert '--replay-manifest "$stage/elisa-proof-replay.manifest.json"' in script
    assert 'pair_json=$(python3 scripts/verify_product_pair.py resolve --generation-root build/elisa-proof-generations)' in script
    assert 'json.load(sys.stdin)["products"]["elisa-proof"]["binary"]' in script
    assert '"$proof_binary" examples/verified.elisa' in script
    assert 'build/elisa-proof examples/verified.elisa' not in script

    with tempfile.TemporaryDirectory(prefix="remote-pair-regression-") as temporary:
        root = Path(temporary)

        # A valid pair has complete identical build inputs even though the binary and
        # per-product build identities are expected to differ.
        binaries, manifests = create_staged_pair(root / "valid")
        generation_root = root / "valid-generations"
        result = publish(generation_root, binaries, manifests)
        assert result.returncode == 0, result.stderr
        resolved = command("resolve", "--generation-root", str(generation_root))
        assert resolved.returncode == 0, resolved.stderr
        pair = json.loads(resolved.stdout)
        assert pair["pair_generation"] == GENERATION
        products = pair["products"]
        assert Path(products["elisa-proof"]["binary"]).parent == Path(
            products["elisa-proof-replay"]["binary"]
        ).parent
        for product in products.values():
            assert product["binary_sha256"] == sha256(Path(product["binary"]))

        mutations = (
            ("frontend revision", lambda data: data["frontend"].update(revision="c" * 40)),
            ("frontend tree", lambda data: data["frontend"].update(tree="f" * 40)),
            ("compiler stage", lambda data: data["compiler"].update(stage="stage0")),
            ("Stage1 revision", lambda data: (data["compiler"].update(
                stage1_revision="c" * 40, source_revision="c" * 40),
                data["frontend"].update(revision="c" * 40))),
            ("compiler source tree", lambda data: data["compiler"].update(source_tree_sha256="c" * 64)),
            ("compiler source state", lambda data: data["compiler"].update(source_dirty=True)),
            ("compiler executable", lambda data: data["compiler"]["executable"].update(sha256="6" * 64)),
            ("compiler product", lambda data: data["compiler"]["product"].update(sha256="7" * 64)),
            ("runtime", lambda data: data["runtime"].update(sha256="8" * 64)),
            ("profile hooks", lambda data: data["profile_hooks"].update(sha256="9" * 64)),
            ("target", lambda data: data.update(target="x86_64-other")),
            ("optimization", lambda data: data.update(optimization="O0")),
            ("compile mode", lambda data: data.update(compile_mode="runtime-checks")),
            ("compiler flags", lambda data: data.update(compiler_flags=["-O0"])),
        )
        for index, (label, mutation) in enumerate(mutations):
            case_root = root / f"mismatch-{index}"
            case_binaries, case_manifests = create_staged_pair(case_root / "staged", mutation)
            rejected = publish(case_root / "generations", case_binaries, case_manifests)
            expected = ("Stage1 source revision differs from imported frontend revision"
                        if label == "frontend revision"
                        else "different toolchain/build identities")
            assert_rejected(rejected, expected)
            assert not (case_root / "generations" / GENERATION).exists(), label

        for missing_field in ("stage1_revision", "source_revision", "source_tree_sha256",
                              "build_recipe_sha256"):
            case_root = root / f"missing-{missing_field}"
            case_binaries, case_manifests = create_staged_pair(case_root / "staged")
            payload = json.loads(case_manifests[0].read_text())
            payload["compiler"][missing_field] = None
            write_manifest(case_manifests[0], payload)
            rejected = publish(case_root / "generations", case_binaries, case_manifests)
            assert rejected.returncode == 2, (missing_field, rejected.stderr)
            assert not (case_root / "generations" / GENERATION).exists(), missing_field

        # A missing identity dimension must fail closed, not degrade to provenance-only
        # comparison. The manifests are correctly resealed so this tests semantic checks.
        missing_root = root / "missing-identity"
        missing_binaries, missing_manifests = create_staged_pair(missing_root / "staged")
        replay_payload = json.loads(missing_manifests[1].read_text())
        replay_payload.pop("compiler_flags")
        write_manifest(missing_manifests[1], replay_payload)
        assert_rejected(
            publish(missing_root / "generations", missing_binaries, missing_manifests),
            "missing shared identity fields",
        )

        # Resolve revalidates the pair after publication, including tampering that has a
        # freshly recomputed manifest checksum and unchanged binary hashes.
        resolve_root = root / "tampered-after-publication"
        resolve_binaries, resolve_manifests = create_staged_pair(resolve_root / "staged")
        published_root = resolve_root / "generations"
        accepted = publish(published_root, resolve_binaries, resolve_manifests)
        assert accepted.returncode == 0, accepted.stderr
        published_replay = published_root / GENERATION / "elisa-proof-replay.manifest.json"
        altered = json.loads(published_replay.read_text())
        altered["target"] = "x86_64-after-publication"
        published_replay.chmod(0o644)
        published_replay.with_name(published_replay.name + ".sha256").chmod(0o644)
        write_manifest(published_replay, altered)
        assert_rejected(
            command("resolve", "--generation-root", str(published_root)),
            "different toolchain/build identities",
        )

        # A source-snapshot mismatch remains an independent rejection condition.
        source_root = root / "source-mismatch"
        source_binaries, source_manifests = create_staged_pair(
            source_root / "staged",
            lambda data: data["proof"].update(head="different-proof-head"),
        )
        assert_rejected(
            publish(source_root / "generations", source_binaries, source_manifests),
            "different source snapshots",
        )

    print("remote build pair publication: shared build identity is required at publish and resolve")


if __name__ == "__main__":
    main()
