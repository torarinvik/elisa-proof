#!/usr/bin/env python3
"""Canonical identity for remote cross-compiled proof objects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compiler_environment import select_compiler_environment  # noqa: E402

SCHEMA = b"elisa-proof-remote-object-v3\0"
REMOTE_OBJECT_RECIPES = (
    Path(__file__).resolve().parent / "build.sh",
    Path(__file__).resolve(),
    Path(__file__).resolve().parents[1] / "compiler_environment.py",
)


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest_tree(root, children):
    root = Path(root)
    files = []
    for child in children:
        base = root / child
        if base.is_file():
            candidates = [base]
        elif base.is_dir():
            candidates = sorted(path for path in base.rglob("*") if path.is_file())
        else:
            raise FileNotFoundError(f"compiler input tree is missing: {base}")
        for path in candidates:
            relative = path.relative_to(root).as_posix()
            files.append((relative, digest_file(path)))
    payload = json.dumps(sorted(files), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def digest_recipes(recipe_files):
    records = []
    for recipe in recipe_files:
        path = Path(os.path.realpath(str(recipe)))
        records.append((str(path), digest_file(path)))
    payload = json.dumps(sorted(records), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def object_cache_key(*, revision, compiler_product, compiler_driver, runtime, opt, main, target,
                     proof_source_root, compiler_source_root, environment, recipe_files=None):
    identity = {
        "schema": 3,
        "compiler_revision": revision,
        "compiler_product_sha256": digest_file(compiler_product),
        "compiler_driver_sha256": digest_file(compiler_driver),
        "runtime_sha256": digest_file(runtime),
        "opt": opt,
        "main": main,
        "target": target,
        "proof_sources_sha256": digest_tree(proof_source_root, ("src",)),
        "compiler_sources_sha256": digest_tree(compiler_source_root, ("src", "elisacore_std")),
        "recipe_sha256": digest_recipes(recipe_files if recipe_files is not None else REMOTE_OBJECT_RECIPES),
        # Bind toolchain/SDK and semantic Elisa inputs. The explicit assignments made by
        # xc_compile are overlaid by the caller before this is filtered and serialized.
        "environment": select_compiler_environment(environment),
        "arguments": ["-emit", "obj", f"-{opt}", "-target-triple", target],
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(SCHEMA + payload).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--compiler-product", required=True)
    parser.add_argument("--compiler-driver", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--opt", required=True)
    parser.add_argument("--main", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--proof-source-root", required=True)
    parser.add_argument("--compiler-source-root", required=True)
    parser.add_argument("--set-env", action="append", default=[])
    args = parser.parse_args()
    environment = dict(os.environ)
    for assignment in args.set_env:
        key, separator, value = assignment.partition("=")
        if not separator or not key:
            parser.error(f"invalid --set-env value: {assignment!r}")
        environment[key] = value
    print(object_cache_key(
        revision=args.revision,
        compiler_product=args.compiler_product,
        compiler_driver=args.compiler_driver,
        runtime=args.runtime,
        opt=args.opt,
        main=args.main,
        target=args.target,
        proof_source_root=args.proof_source_root,
        compiler_source_root=args.compiler_source_root,
        environment=environment,
    ))


if __name__ == "__main__":
    main()
