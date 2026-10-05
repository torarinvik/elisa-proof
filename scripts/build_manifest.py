"""Write the reproducible evidence manifest for one elisa-proof build.

The manifest names everything that decides what the proof executable computes: the proof
sources that were compiled, the compiler frontend revision and tree they were compiled
against, the compiler product and stage that emitted the object, the runtime and profiler
objects linked into it, the target, optimization level and compile mode. It is evidence
only; nothing in the proof checker reads it.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from compiler_environment import select_compiler_environment

MANIFEST_SCHEMA = "elisa-proof-build-manifest-v1"
INCLUDE_RE = re.compile(r'^\s*include\s+"([^"]+)"', re.MULTILINE)


def effective_environment() -> dict:
    """Return only environment controls that can affect compiler/link outputs."""
    return select_compiler_environment(os.environ)


def effective_environment_digest() -> str:
    encoded = json.dumps(effective_environment(), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path: str) -> dict:
    if not path:
        return {"path": None, "sha256": None}
    real = os.path.realpath(path)
    digest = hashlib.sha256()
    with open(real, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return {"path": real, "sha256": digest.hexdigest(), "bytes": os.path.getsize(real)}


def tree_digest(root: str) -> str:
    """Hash every file under root by relative path and contents, in a fixed order."""
    digest = hashlib.sha256()
    for directory, subdirectories, files in os.walk(root):
        subdirectories.sort()
        for name in sorted(files):
            path = os.path.join(directory, name)
            relative = os.path.relpath(path, root).replace(os.sep, "/")
            digest.update(relative.encode() + b"\0")
            with open(path, "rb") as handle:
                digest.update(hashlib.sha256(handle.read()).digest())
    return digest.hexdigest()


def dependency_digest(root: str, main: str) -> str:
    """Hash the transitive textual include closure for one proof product."""
    root = os.path.realpath(root)
    pending = [os.path.realpath(os.path.join(root, main))]
    visited = set()
    digest = hashlib.sha256()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        try:
            with open(path, "rb") as handle:
                contents = handle.read()
        except OSError as error:
            raise ValueError(f"missing include dependency {path}: {error}") from error
        # Include paths may point from the proof snapshot into its adjacent pinned
        # compiler export, but may not escape the snapshot directory's parent.
        allowed_root = os.path.dirname(root)
        if os.path.commonpath((allowed_root, path)) != allowed_root:
            raise ValueError(f"include dependency escapes snapshot: {path}")
        relative = os.path.relpath(path, allowed_root).replace(os.sep, "/")
        digest.update(relative.encode() + b"\0" + hashlib.sha256(contents).digest())
        text = contents.decode("utf-8")
        for include in INCLUDE_RE.findall(text):
            pending.append(os.path.realpath(os.path.join(os.path.dirname(path), include)))
    return digest.hexdigest()


def git(repository: str, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", repository, *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def target_triple(clang: str = "clang") -> str:
    try:
        result = subprocess.run([clang, "-dumpmachine"], check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return f"{platform.machine()}-{platform.system().lower()}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dependency-root", default="")
    parser.add_argument("--dependency-main", default="")
    parser.add_argument("--identity-only", action="store_true")
    parser.add_argument("--identity-root", default="")
    parser.add_argument("--identity-main", default="")
    parser.add_argument("--identity-object-key", default="")
    parser.add_argument("--identity-compiler", default="")
    parser.add_argument("--identity-compiler-product", default="")
    parser.add_argument("--identity-clang", default="")
    parser.add_argument("--identity-link-input", action="append", default=[])
    parser.add_argument("--identity-recipe", action="append", default=[])
    parser.add_argument("--recipes-digest", action="store_true")
    parser.add_argument("--recipe-path", action="append", default=[])
    parser.add_argument("--identity-link-flags", default="")
    parser.add_argument("--identity-output", default="")
    parser.add_argument("--check-existing", action="store_true")
    parser.add_argument("--refresh-proof-provenance", action="store_true")
    parser.add_argument("--refresh-manifest", default="")
    parser.add_argument("--refresh-snapshot-root", default="")
    parser.add_argument("--refresh-proof-root", default="")
    parser.add_argument("--existing-binary", default="")
    parser.add_argument("--existing-manifest", default="")
    parser.add_argument("--existing-manifest-sha256", default="")
    parser.add_argument("--recorded-build-identity", default="")
    parser.add_argument("--target-clang", default="clang")
    parser.add_argument("--effective-env-digest", action="store_true")
    for option in (
        "binary", "compiler", "stage", "stage1-revision", "runtime", "profile-hooks",
        "frontend-repo", "frontend-revision", "proof-root", "snapshot-root",
        "opt-level", "compile-mode", "contract-flag", "installed-as", "output",
        "compiler-product", "compiler-root",
    ):
        parser.add_argument(f"--{option}", default="")
    arguments = parser.parse_args()

    if arguments.effective_env_digest:
        print(effective_environment_digest())
        return 0

    if arguments.recipes_digest:
        try:
            recipes = [file_digest(path) for path in arguments.recipe_path]
        except OSError as error:
            print(f"build manifest: cannot hash build recipes: {error}", file=sys.stderr)
            return 2
        encoded = json.dumps(recipes, sort_keys=True, separators=(",", ":")).encode()
        print(hashlib.sha256(encoded).hexdigest())
        return 0

    if arguments.identity_only:
        required = (arguments.identity_root, arguments.identity_main, arguments.identity_object_key,
                    arguments.identity_compiler, arguments.identity_compiler_product,
                    arguments.identity_clang, arguments.identity_output)
        if not all(required):
            print("build manifest: incomplete build identity inputs", file=sys.stderr)
            return 2
        try:
            closure = dependency_digest(arguments.identity_root, arguments.identity_main)
            clang_version = subprocess.run([arguments.identity_clang, "--version"], check=True,
                                           capture_output=True, text=True).stdout.splitlines()[0]
            clang_target = subprocess.run([arguments.identity_clang, "-dumpmachine"], check=True,
                                          capture_output=True, text=True).stdout.strip()
            clang_resource = subprocess.run([arguments.identity_clang, "-print-resource-dir"], check=True,
                                            capture_output=True, text=True).stdout.strip()
            linker = shutil.which("ld") or ""
            linker_version = ""
            if linker:
                result = subprocess.run([linker, "--version"], capture_output=True, text=True)
                linker_version = (result.stdout or result.stderr).splitlines()[0]
            sdk = {}
            if platform.system() == "Darwin" and shutil.which("xcrun"):
                for key, command in (
                    ("path", ["xcrun", "--sdk", "macosx", "--show-sdk-path"]),
                    ("version", ["xcrun", "--sdk", "macosx", "--show-sdk-version"]),
                ):
                    result = subprocess.run(command, capture_output=True, text=True)
                    sdk[key] = result.stdout.strip() if result.returncode == 0 else ""
            payload = {
                "proof_closure": closure,
                "object_key": arguments.identity_object_key,
                "compiler": file_digest(arguments.identity_compiler),
                "compiler_product": file_digest(arguments.identity_compiler_product),
                "clang": file_digest(arguments.identity_clang),
                "clang_version": clang_version,
                "clang_target": clang_target,
                "clang_resource_dir": clang_resource,
                "linker": file_digest(linker),
                "linker_version": linker_version,
                "sdk": sdk,
                "link_inputs": [file_digest(path) for path in arguments.identity_link_input],
                "build_recipes": [file_digest(path) for path in arguments.identity_recipe],
                "link_flags": arguments.identity_link_flags,
                "output": os.path.realpath(arguments.identity_output),
                "effective_environment_sha256": effective_environment_digest(),
                "platform": {"system": platform.system(), "machine": platform.machine()},
            }
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            print(hashlib.sha256(encoded).hexdigest())
        except (OSError, subprocess.CalledProcessError, ValueError, IndexError) as error:
            print(f"build manifest: cannot compute build identity: {error}", file=sys.stderr)
            return 2
        return 0

    if arguments.check_existing:
        try:
            with open(arguments.existing_manifest, encoding="utf-8") as handle:
                previous = json.load(handle)
            current_digest = file_digest(arguments.existing_binary)["sha256"]
            manifest_digest = file_digest(arguments.existing_manifest)["sha256"]
            with open(arguments.existing_manifest_sha256, encoding="ascii") as handle:
                recorded_manifest_digest = handle.read().strip()
            matches = (previous.get("build_identity") == arguments.recorded_build_identity
                       and previous.get("binary", {}).get("sha256") == current_digest
                       and manifest_digest == recorded_manifest_digest
                       and current_digest is not None)
        except (OSError, json.JSONDecodeError, TypeError):
            matches = False
        return 0 if matches else 1

    if arguments.refresh_proof_provenance:
        if not all((arguments.refresh_manifest, arguments.refresh_snapshot_root,
                    arguments.refresh_proof_root)):
            print("build manifest: provenance refresh requires manifest, snapshot and proof roots",
                  file=sys.stderr)
            return 2
        manifest_path = os.path.realpath(arguments.refresh_manifest)
        checksum_path = manifest_path + ".sha256"
        try:
            with open(manifest_path, encoding="utf-8") as handle:
                manifest = json.load(handle)
            current_proof = {
                "head": git(arguments.refresh_proof_root, "rev-parse", "HEAD") or None,
                "source_dirty": bool(git(arguments.refresh_proof_root, "status", "--porcelain", "--", "src")),
                "source_tree_sha256": tree_digest(os.path.join(arguments.refresh_snapshot_root, "src")),
            }
            if manifest.get("proof") == current_proof:
                return 0
            manifest["proof"] = current_proof
            encoded = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
            digest = hashlib.sha256(encoded).hexdigest()
            token = str(os.getpid())
            manifest_temp = manifest_path + ".tmp." + token
            checksum_temp = checksum_path + ".tmp." + token
            with open(manifest_temp, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            with open(checksum_temp, "w", encoding="ascii") as handle:
                handle.write(digest + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            # A reader seeing the brief mixed generation rejects it via the checksum sidecar.
            os.replace(manifest_temp, manifest_path)
            os.replace(checksum_temp, checksum_path)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            print(f"build manifest: cannot refresh proof provenance: {error}", file=sys.stderr)
            return 2
        return 0

    if arguments.dependency_root or arguments.dependency_main:
        if not arguments.dependency_root or not arguments.dependency_main:
            print("build manifest: --dependency-root and --dependency-main must be used together", file=sys.stderr)
            return 2
        try:
            print(dependency_digest(arguments.dependency_root, arguments.dependency_main))
        except (OSError, ValueError) as error:
            print(f"build manifest: {error}", file=sys.stderr)
            return 2
        return 0

    if arguments.stage not in ("stage0", "stage1"):
        print(f"build manifest: unknown compiler stage {arguments.stage!r}", file=sys.stderr)
        return 2
    if arguments.stage == "stage1" and not arguments.runtime:
        print("build manifest: a stage1 product must name the runtime object it links", file=sys.stderr)
        return 2

    proof_head = git(arguments.proof_root, "rev-parse", "HEAD")
    proof_status = git(arguments.proof_root, "status", "--porcelain", "--", "src")
    frontend_tree = git(arguments.frontend_repo, "rev-parse", f"{arguments.frontend_revision}^{{tree}}")
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "build_identity": arguments.recorded_build_identity or None,
        "proof": {
            "head": proof_head or None,
            "source_dirty": bool(proof_status),
            "source_tree_sha256": tree_digest(os.path.join(arguments.snapshot_root, "src")),
        },
        "frontend": {
            "revision": arguments.frontend_revision,
            "tree": frontend_tree or None,
        },
        "compiler": {
            "stage": arguments.stage,
            "stage1_revision": arguments.stage1_revision or None,
            "executable": file_digest(arguments.compiler),
            # A stage1 driver is a wrapper script; the product it runs is what emits code.
            "product": file_digest(arguments.compiler_product),
            "source_revision": git(arguments.compiler_root, "rev-parse", "HEAD") or None if arguments.compiler_root else None,
            "source_dirty": bool(git(arguments.compiler_root, "status", "--porcelain", "--untracked-files=no")) if arguments.compiler_root else None,
        },
        "runtime": file_digest(arguments.runtime),
        "profile_hooks": file_digest(arguments.profile_hooks),
        "target": target_triple(arguments.target_clang),
        "optimization": arguments.opt_level,
        "compile_mode": arguments.compile_mode,
        "compiler_flags": [flag for flag in (arguments.contract_flag, "-emit", "obj", f"-{arguments.opt_level}") if flag],
        "binary": file_digest(arguments.binary),
    }
    if arguments.installed_as:
        manifest["binary"]["path"] = os.path.realpath(arguments.installed_as)
    with open(arguments.output, "w") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
