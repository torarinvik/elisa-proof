"""Product object keys follow textual include dependencies, not every src file."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts/build_manifest.py"


def digest(snapshot: Path, main: str) -> str:
    result = subprocess.run(
        ["python3", str(MANIFEST), "--dependency-root", str(snapshot),
         "--dependency-main", main],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def identity(snapshot: Path, main: str, compiler: Path, clang: str, link_input: Path,
             output: Path, environment=None) -> str:
    result = subprocess.run(
        ["python3", str(MANIFEST), "--identity-only", "--identity-root", str(snapshot),
         "--identity-main", main, "--identity-object-key", "object-key",
         "--identity-compiler", str(compiler), "--identity-compiler-product", str(compiler),
         "--identity-clang", clang, "--identity-link-input", str(link_input),
         "--identity-link-flags=-dead_strip", "--identity-output", str(output)],
        check=True, capture_output=True, text=True, env=environment,
    )
    return result.stdout.strip()


with tempfile.TemporaryDirectory(prefix="elisa-build-closure-") as directory:
    base = Path(directory)
    proof = base / "elisa-proof"
    compiler = base / "Elisa-compiler"
    (proof / "src").mkdir(parents=True)
    (compiler / "src").mkdir(parents=True)
    (proof / "src/main.elisa").write_text('include "./shared.elisa"\nmain\n')
    (proof / "src/replay_main.elisa").write_text("replay\n")
    (proof / "src/shared.elisa").write_text('include "../../Elisa-compiler/src/front.elisa"\nshared\n')
    (proof / "src/unrelated.elisa").write_text("unrelated\n")
    (compiler / "src/front.elisa").write_text("frontend\n")

    main_before = digest(proof, "src/main.elisa")
    replay_before = digest(proof, "src/replay_main.elisa")
    (proof / "src/unrelated.elisa").write_text("unrelated edit\n")
    assert digest(proof, "src/main.elisa") == main_before
    assert digest(proof, "src/replay_main.elisa") == replay_before
    (compiler / "src/front.elisa").write_text("frontend edit\n")
    assert digest(proof, "src/main.elisa") != main_before
    assert digest(proof, "src/replay_main.elisa") == replay_before

    clang = shutil.which("clang")
    if clang:
        fake_compiler = base / "compiler.bin"
        fake_compiler.write_bytes(b"compiler")
        linked = base / "linked.o"
        linked.write_bytes(b"hooks")
        output = base / "proof-bin"
        output.write_bytes(b"binary")
        proof_identity = identity(proof, "src/replay_main.elisa", fake_compiler,
                                  clang, linked, output)
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output) == proof_identity
        build_jobs_env = dict(os.environ, ELISA_PROOF_BUILD_JOBS="9")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, build_jobs_env) == proof_identity
        linked.write_bytes(b"changed hooks")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output) != proof_identity

        manifest = base / "proof-bin.manifest.json"
        manifest.write_text(json.dumps({"build_identity": proof_identity,
                                        "binary": {"sha256": hashlib.sha256(output.read_bytes()).hexdigest()}}))
        manifest_hash = base / "proof-bin.manifest.json.sha256"
        manifest_hash.write_text(hashlib.sha256(manifest.read_bytes()).hexdigest())
        check = ["python3", str(MANIFEST), "--check-existing", "--recorded-build-identity",
                 proof_identity, "--existing-binary", str(output), "--existing-manifest", str(manifest),
                 "--existing-manifest-sha256", str(manifest_hash)]
        assert subprocess.run(check).returncode == 0
        output.write_bytes(b"tampered binary")
        assert subprocess.run(check).returncode == 1
print("build dependency closure: unrelated edits are excluded and transitive includes invalidate")
