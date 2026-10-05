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
             output: Path, environment=None, recipe: Path = None) -> str:
    command = ["python3", str(MANIFEST), "--identity-only", "--identity-root", str(snapshot),
         "--identity-main", main, "--identity-object-key", "object-key",
         "--identity-compiler", str(compiler), "--identity-compiler-product", str(compiler),
         "--identity-clang", clang, "--identity-link-input", str(link_input),
         "--identity-link-flags=-dead_strip", "--identity-output", str(output)]
    if recipe is not None:
        command.extend(["--identity-recipe", str(recipe)])
    result = subprocess.run(command, check=True, capture_output=True, text=True, env=environment)
    return result.stdout.strip()


def env_digest(environment=None) -> str:
    result = subprocess.run(["python3", str(MANIFEST), "--effective-env-digest"],
                            check=True, capture_output=True, text=True, env=environment)
    return result.stdout.strip()


def recipes_digest(recipe: Path) -> str:
    result = subprocess.run(
        ["python3", str(MANIFEST), "--recipes-digest", "--recipe-path", str(recipe)],
        check=True, capture_output=True, text=True,
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
    main_current = digest(proof, "src/main.elisa")
    replay_current = digest(proof, "src/replay_main.elisa")

    clang = shutil.which("clang")
    if clang:
        fake_compiler = base / "compiler.bin"
        fake_compiler.write_bytes(b"compiler")
        linked = base / "linked.o"
        linked.write_bytes(b"hooks")
        recipe = base / "build.sh"
        recipe.write_text("build recipe v1\n")
        first_recipe_digest = recipes_digest(recipe)
        output = base / "proof-bin"
        output.write_bytes(b"binary")
        main_output = base / "main-bin"
        main_output.write_bytes(b"binary")
        main_identity = identity(proof, "src/main.elisa", fake_compiler,
                                 clang, linked, main_output, recipe=recipe)
        proof_identity = identity(proof, "src/replay_main.elisa", fake_compiler,
                                  clang, linked, output, recipe=recipe)
        (proof / "src/unrelated.elisa").write_text("another unrelated edit\n")
        assert digest(proof, "src/main.elisa") == main_current
        assert digest(proof, "src/replay_main.elisa") == replay_current
        assert identity(proof, "src/main.elisa", fake_compiler,
                        clang, linked, main_output, recipe=recipe) == main_identity
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, recipe=recipe) == proof_identity
        build_jobs_env = dict(os.environ, ELISA_PROOF_BUILD_JOBS="9")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, build_jobs_env, recipe) == proof_identity
        unrelated_env = dict(os.environ, CODEX_THREAD_ID="different-session", TERM="vt100")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, unrelated_env, recipe) == proof_identity
        relevant_env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET="12.0")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, relevant_env, recipe) != proof_identity
        target_env = dict(os.environ, ELISA_TARGET_TRIPLE="aarch64-unknown-test")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, target_env, recipe) != proof_identity
        path_env = dict(os.environ, PATH="/p03-other-tools:" + os.environ.get("PATH", ""))
        sdk_env = dict(os.environ, SDKROOT="")
        assert env_digest(build_jobs_env) == env_digest(unrelated_env)
        assert env_digest(unrelated_env) != env_digest(relevant_env)
        assert env_digest(unrelated_env) != env_digest(target_env)
        assert env_digest(unrelated_env) != env_digest(path_env)
        assert env_digest(unrelated_env) != env_digest(sdk_env)
        linked.write_bytes(b"changed hooks")
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, recipe=recipe) != proof_identity
        recipe.write_text("build recipe v2\n")
        assert recipes_digest(recipe) != first_recipe_digest
        assert identity(proof, "src/replay_main.elisa", fake_compiler,
                        clang, linked, output, recipe=recipe) != proof_identity

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
