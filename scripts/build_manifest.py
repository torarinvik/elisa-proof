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
import subprocess
import sys

MANIFEST_SCHEMA = "elisa-proof-build-manifest-v1"


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


def target_triple() -> str:
    try:
        result = subprocess.run(["clang", "-dumpmachine"], check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return f"{platform.machine()}-{platform.system().lower()}"


def main() -> int:
    parser = argparse.ArgumentParser()
    for option in (
        "binary", "compiler", "stage", "stage1-revision", "runtime", "profile-hooks",
        "frontend-repo", "frontend-revision", "proof-root", "snapshot-root",
        "opt-level", "compile-mode", "contract-flag", "installed-as", "output",
        "compiler-product", "compiler-root",
    ):
        parser.add_argument(f"--{option}", default="")
    arguments = parser.parse_args()

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
        "target": target_triple(),
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
