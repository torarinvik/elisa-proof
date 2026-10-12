"""Validate the provenance chain for an imported Stage1 compiler product."""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from build_manifest_hashes import file_digest

SUPPORTED_STAGE1_PROVENANCE_SCHEMAS = frozenset({
    "elisa-stage1-provenance-v1",
    "elisa-stage1-provenance-v5",
})

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


def committed_compiler_source_digest(repository: str, revision: str) -> str:
    """Hash the compiler source/stdlib files exactly as Stage1 records them."""
    try:
        result = subprocess.run(
            ["git", "-C", repository, "archive", "--format=tar", revision,
             "src", "elisacore_std"],
            check=True,
            capture_output=True,
        )
        digest = hashlib.sha256()
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            files = []
            for member in archive.getmembers():
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError(
                        f"unsupported non-file compiler source in pinned tree: {member.name}"
                    )
                name = member.name.rstrip("/")
                if (name.startswith("/") or ".." in name.split("/")
                        or not name.startswith(("src/", "elisacore_std/"))):
                    raise ValueError(f"invalid compiler source path in pinned tree: {name}")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"cannot read compiler source in pinned tree: {name}")
                files.append((name, stream.read()))
        for name, contents in sorted(files):
            digest.update(name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(contents)
            digest.update(b"\0")
        if not files:
            raise ValueError("pinned compiler tree has no source files")
        return digest.hexdigest()
    except (OSError, subprocess.CalledProcessError, tarfile.TarError) as error:
        raise ValueError(f"cannot inspect pinned compiler source tree: {error}") from error


LEGACY_RECIPE_PATHS = (
    "scripts/elisac_stage1.sh",
    "scripts/elisac_stage1_seed.sh",
    "scripts/build_runtime_object.sh",
    "scripts/write_profiler_hook_fallbacks.sh",
)


def committed_recipe_paths(repository: str, revision: str) -> tuple:
    """Read the recipe list Stage1 hashes from its pinned provenance script."""
    try:
        script = subprocess.run(
            ["git", "-C", repository, "show", f"{revision}:scripts/stage1_provenance.py"],
            check=True, capture_output=True, text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return LEGACY_RECIPE_PATHS
    for node in ast.parse(script).body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "BUILD_RECIPES"):
            try:
                paths = ast.literal_eval(node.value)
            except ValueError as error:
                raise ValueError(f"cannot evaluate pinned BUILD_RECIPES: {error}") from error
            if (not isinstance(paths, (tuple, list)) or not paths
                    or not all(isinstance(path, str) for path in paths)):
                raise ValueError("pinned BUILD_RECIPES is not a non-empty list of paths")
            return tuple(paths)
    return LEGACY_RECIPE_PATHS


def committed_compiler_recipe_digest(repository: str, revision: str) -> str:
    """Hash the build recipes Stage1 records, directly from the pinned commit."""
    recipe_paths = committed_recipe_paths(repository, revision)
    try:
        result = subprocess.run(
            ["git", "-C", repository, "archive", "--format=tar", revision,
             *recipe_paths],
            check=True,
            capture_output=True,
        )
        digest = hashlib.sha256()
        files = []
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            for member in archive.getmembers():
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError(f"unsupported non-file compiler recipe: {member.name}")
                name = member.name.rstrip("/")
                if name not in recipe_paths:
                    raise ValueError(f"unexpected compiler recipe path in pinned tree: {name}")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"cannot read compiler recipe in pinned tree: {name}")
                files.append((name, stream.read()))
        for name, contents in sorted(files):
            digest.update(name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(contents)
            digest.update(b"\0")
        if len(files) != len(recipe_paths):
            raise ValueError("pinned compiler commit is missing one or more Stage1 build recipes")
        return digest.hexdigest()
    except (OSError, subprocess.CalledProcessError, tarfile.TarError) as error:
        raise ValueError(f"cannot inspect pinned compiler build recipes: {error}") from error


def committed_stage1_provenance_schema(repository: str, revision: str) -> str:
    """Read the provenance protocol emitted by the exact pinned compiler source."""
    source = git(repository, "show", f"{revision}:scripts/stage1_provenance.py")
    if not source:
        # Very old compiler snapshots predate a schema declaration and used v1 records.
        return "elisa-stage1-provenance-v1"
    try:
        module = ast.parse(source)
    except SyntaxError as error:
        raise ValueError(f"pinned Stage1 provenance script is invalid: {error}") from error
    for statement in module.body:
        if (isinstance(statement, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "SCHEMA"
                        for target in statement.targets)):
            try:
                schema = ast.literal_eval(statement.value)
            except (ValueError, TypeError) as error:
                raise ValueError("pinned Stage1 provenance SCHEMA is not a literal") from error
            if not isinstance(schema, str):
                raise ValueError("pinned Stage1 provenance SCHEMA is not a string")
            return schema
    return "elisa-stage1-provenance-v1"


def _valid_stage1_artifact(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    if not isinstance(value.get("path"), str) or not value["path"]:
        return False
    if not isinstance(value.get("sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is None:
        return False
    return all(type(value.get(key)) is int and value[key] >= 0
               for key in ("size", "mtime_ns", "ctime_ns", "device", "inode"))


def validate_stage1_v5_shape(provenance: dict) -> None:
    """Reject v5 labels that omit the producer's toolchain or seed identity records."""
    toolchain = provenance.get("llvm_toolchain")
    seed = provenance.get("seed_configuration")
    if not isinstance(toolchain, dict):
        raise ValueError("Stage1 v5 provenance is missing its LLVM toolchain record")
    if not isinstance(seed, dict):
        raise ValueError("Stage1 v5 provenance is missing its seed configuration record")

    string_fields = (
        "llvm_config_path", "llvm_version", "llvm_bindir", "llvm_libdir",
        "llvm_config_libdir", "clang_path", "clang_version", "link_mode", "link_flags",
    )
    if any(not isinstance(toolchain.get(key), str) for key in string_fields):
        raise ValueError("Stage1 v5 provenance has an incomplete LLVM toolchain record")
    if any(not toolchain[key] for key in (
            "llvm_config_path", "llvm_bindir", "llvm_libdir", "llvm_config_libdir", "clang_path")):
        raise ValueError("Stage1 v5 provenance has an empty LLVM toolchain path")
    if toolchain["link_mode"] not in ("static", "dynamic"):
        raise ValueError("Stage1 v5 provenance has an unknown LLVM link mode")
    if not _valid_stage1_artifact(toolchain.get("llvm_config_artifact")):
        raise ValueError("Stage1 v5 provenance has an invalid llvm-config artifact")
    if not _valid_stage1_artifact(toolchain.get("clang_artifact")):
        raise ValueError("Stage1 v5 provenance has an invalid clang artifact")
    linker = toolchain.get("external_linker")
    if (not isinstance(linker, dict)
            or any(not isinstance(linker.get(key), str)
                   for key in ("command", "path", "version"))
            or not linker["command"] or not linker["path"]
            or not _valid_stage1_artifact(linker.get("artifact"))
            or not isinstance(linker.get("link_command"), list)
            or not all(isinstance(argument, str) for argument in linker["link_command"])
            or not isinstance(linker.get("clang_artifact_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", linker["clang_artifact_sha256"]) is None
            or not isinstance(linker.get("linker_probe_cache_key"), str)
            or re.fullmatch(r"[0-9a-f]{64}", linker["linker_probe_cache_key"]) is None):
        raise ValueError("Stage1 v5 provenance has an incomplete external linker record")
    if (toolchain["llvm_config_path"] != toolchain["llvm_config_artifact"]["path"]
            or toolchain["clang_path"] != toolchain["clang_artifact"]["path"]
            or linker["path"] != linker["artifact"]["path"]
            or linker["clang_artifact_sha256"] != toolchain["clang_artifact"]["sha256"]):
        raise ValueError("Stage1 v5 provenance toolchain paths and artifact identities disagree")
    for key in ("dynamic_libraries", "static_archives", "link_libraries"):
        values = toolchain.get(key)
        if not isinstance(values, list) or not all(_valid_stage1_artifact(value) for value in values):
            raise ValueError(f"Stage1 v5 provenance has an invalid {key} record")

    bootstrap = seed.get("bootstrap_compiler")
    if not _valid_stage1_artifact(bootstrap):
        raise ValueError("Stage1 v5 provenance has an invalid bootstrap compiler identity")
    if seed.get("bootstrap_kind") not in ("stage0", "stage1"):
        raise ValueError("Stage1 v5 provenance has an unknown bootstrap compiler kind")
    if seed.get("optimization_level") not in ("-O0", "-O1", "-O2", "-O3"):
        raise ValueError("Stage1 v5 provenance has an invalid seed optimization level")
    runtime = seed.get("bootstrap_runtime_object")
    if runtime is not None and not _valid_stage1_artifact(runtime):
        raise ValueError("Stage1 v5 provenance has an invalid bootstrap runtime identity")
    expected_runtime = seed.get("bootstrap_runtime_expected_sha256")
    if (expected_runtime is not None
            and (not isinstance(expected_runtime, str)
                 or re.fullmatch(r"[0-9a-f]{64}", expected_runtime) is None)):
        raise ValueError("Stage1 v5 provenance has an invalid bootstrap runtime digest")
    if runtime is None and expected_runtime is not None:
        raise ValueError("Stage1 v5 provenance has a runtime digest without a runtime object")
    expected_link_mode = "static-object" if runtime is not None else "none"
    if seed.get("bootstrap_runtime_link_mode") != expected_link_mode:
        raise ValueError("Stage1 v5 provenance has an inconsistent bootstrap runtime mode")
    if runtime is not None and expected_runtime != runtime["sha256"]:
        raise ValueError("Stage1 v5 provenance bootstrap runtime digest does not match its artifact")
    for key in (
        "host_os", "elisa_host_os", "seed_link_flags", "executable_link_flags",
        "dead_strip_flags", "stack_flags", "llvm_link_flags", "profiler_hook_mode",
    ):
        if not isinstance(seed.get(key), str):
            raise ValueError("Stage1 v5 provenance has an incomplete seed configuration record")
    if seed.get("clang_path") is not None and not isinstance(seed["clang_path"], str):
        raise ValueError("Stage1 v5 provenance has an invalid seed clang path")


def verify_stage1_v5_exact_inputs(product: str, compiler_root: str,
                                  frontend_repo: str, revision: str) -> None:
    """Run the pinned v5 checker against an extracted exact source/recipe snapshot."""
    recipes = committed_recipe_paths(frontend_repo, revision)
    if "scripts/stage1_provenance.py" not in recipes:
        raise ValueError("pinned v5 Stage1 provenance checker is absent from its build recipes")
    try:
        result = subprocess.run(
            ["git", "-C", frontend_repo, "archive", "--format=tar", revision,
             "src", "elisacore_std", *recipes],
            check=True, capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"cannot extract pinned Stage1 inputs for exact verification: {error}") from error

    try:
        with tempfile.TemporaryDirectory(prefix="elisa-stage1-verify-") as temporary:
            snapshot = Path(temporary)
            (snapshot / "SNAPSHOT").write_text(
                f"source_revision: {revision}\n", encoding="ascii",
            )
            try:
                with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
                    for member in archive.getmembers():
                        if member.isdir():
                            continue
                        relative = Path(member.name)
                        if (not member.isfile() or relative.is_absolute()
                                or ".." in relative.parts or not relative.parts):
                            raise ValueError("pinned Stage1 input archive has an unsupported path")
                        allowed = (relative.parts[0] in ("src", "elisacore_std")
                                   or relative.as_posix() in recipes)
                        if not allowed:
                            raise ValueError("pinned Stage1 input archive contains an unexpected path")
                        stream = archive.extractfile(member)
                        if stream is None:
                            raise ValueError("cannot read pinned Stage1 input archive member")
                        destination = snapshot / relative
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(stream.read())
                        # Exact content hashes, not archive timestamps, qualify these files.
                        os.utime(destination, ns=(0, 0))
            except tarfile.TarError as error:
                raise ValueError(f"cannot read pinned Stage1 input archive: {error}") from error

            checker = snapshot / "scripts/stage1_provenance.py"
            check = subprocess.run(
                [sys.executable, str(checker), "check-exact", str(snapshot), product],
                capture_output=True, text=True,
            )
            if check.returncode != 0:
                detail = (check.stderr or check.stdout).strip()
                raise ValueError(
                    "Stage1 v5 exact toolchain/seed verification failed"
                    + (f": {detail}" if detail else "")
                )
    except OSError as error:
        raise ValueError(f"cannot execute the pinned Stage1 exact checker: {error}") from error


def verify_stage1_v5_seed_chain(product: str, provenance: dict, frontend_repo: str,
                                pinned_stage0_revision: str,
                                seen_products: set[str]) -> None:
    """Bind the recorded v5 seed artifact recursively to the repository's Stage0 pin."""
    if re.fullmatch(r"[0-9a-f]{40}", pinned_stage0_revision) is None:
        raise ValueError("Stage1 v5 qualification requires an exact ELISA_STAGE0_REV")
    seed = provenance["seed_configuration"]
    bootstrap = seed["bootstrap_compiler"]
    bootstrap_path = bootstrap["path"]
    if file_digest(bootstrap_path)["sha256"] != bootstrap["sha256"]:
        raise ValueError("Stage1 bootstrap compiler changed after exact provenance verification")
    if seed["bootstrap_kind"] == "stage0":
        try:
            result = subprocess.run(
                ["go", "version", "-m", bootstrap_path],
                check=True, capture_output=True, text=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise ValueError(f"cannot inspect Stage1's Stage0 bootstrap compiler: {error}") from error
        validate_stage0_build_info(result.stdout, pinned_stage0_revision)
        return

    resolved_product = os.path.realpath(product)
    if resolved_product in seen_products:
        raise ValueError("Stage1 bootstrap provenance contains a cycle")
    nested_path = Path(str(bootstrap_path) + ".provenance.json")
    try:
        nested = json.loads(nested_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Stage1 bootstrap provenance is unavailable: {error}") from error
    if not isinstance(nested, dict) or nested.get("schema") != "elisa-stage1-provenance-v5":
        raise ValueError("Stage1 bootstrap lacks v5 provenance needed to verify its seed chain")
    nested_revision = nested.get("source_revision")
    if not isinstance(nested_revision, str):
        raise ValueError("Stage1 bootstrap provenance has no source revision")
    validated_stage1_provenance(
        bootstrap_path, "", frontend_repo, nested_revision,
        pinned_stage0_revision=pinned_stage0_revision,
        require_stage0_binding=True,
        seen_products=seen_products | {resolved_product},
    )


def validate_stage0_build_info(build_info: str, pinned_revision: str) -> str:
    """Verify a Go Stage0 compiler embeds the pinned revision and clean-source marker."""
    revision = ""
    modified = ""
    for line in build_info.splitlines():
        fields = line.split()
        if not fields or fields[0] != "build":
            continue
        for field in fields[1:]:
            if field.startswith("vcs.revision="):
                revision = field.removeprefix("vcs.revision=")
            elif field.startswith("vcs.modified="):
                modified = field.removeprefix("vcs.modified=")
    if not pinned_revision or not revision.startswith(pinned_revision):
        raise ValueError("Stage0 binary revision does not match ELISA_STAGE0_REV")
    if modified != "false":
        raise ValueError("Stage0 binary was built from modified sources or lacks VCS cleanliness")
    return revision


def validated_stage1_provenance(product: str, compiler_root: str,
                                frontend_repo: str, frontend_revision: str,
                                *, pinned_stage0_revision: str = "",
                                require_stage0_binding: bool = False,
                                seen_products: set[str] | None = None) -> dict:
    """Validate and return Stage1 provenance against the exact imported frontend commit."""
    if not all((product, frontend_repo, frontend_revision)):
        raise ValueError("Stage1 provenance requires product and pinned frontend inputs")
    provenance_path = f"{product}.provenance.json"
    try:
        with open(provenance_path, encoding="utf-8") as handle:
            provenance = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Stage1 provenance unavailable at {provenance_path}: {error}") from error
    # Stage1 v5 adds exact source/toolchain input fingerprints while preserving the v1
    # content-addressed core checked below. Pin supported protocols explicitly so a future
    # schema cannot silently change the meaning of those fields.
    if (not isinstance(provenance, dict)
            or provenance.get("schema") not in SUPPORTED_STAGE1_PROVENANCE_SCHEMAS):
        raise ValueError("Stage1 provenance has an unknown or malformed schema")
    schema = provenance["schema"]

    source_revision = provenance.get("source_revision")
    source_tree = provenance.get("source_tree_sha256")
    build_recipe = provenance.get("build_recipe_sha256")
    product_sha256 = provenance.get("product_sha256")
    if not isinstance(source_revision, str) or re.fullmatch(r"[0-9a-f]{40}", source_revision) is None:
        raise ValueError("Stage1 provenance is missing an exact committed source revision")
    if not isinstance(source_tree, str) or re.fullmatch(r"[0-9a-f]{64}", source_tree) is None:
        raise ValueError("Stage1 provenance is missing a valid source-tree digest")
    if not isinstance(build_recipe, str) or re.fullmatch(r"[0-9a-f]{64}", build_recipe) is None:
        raise ValueError("Stage1 provenance is missing a valid build-recipe digest")
    if not isinstance(product_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", product_sha256) is None:
        raise ValueError("Stage1 provenance is missing a valid product digest")
    actual_product = file_digest(product)["sha256"]
    if product_sha256 != actual_product:
        raise ValueError("Stage1 product is stale: product digest differs from its provenance")

    pinned_revision = git(frontend_repo, "rev-parse", "--verify",
                          f"{frontend_revision}^{{commit}}")
    if not pinned_revision:
        raise ValueError(f"cannot resolve pinned frontend commit {frontend_revision!r}")
    pinned_schema = committed_stage1_provenance_schema(frontend_repo, pinned_revision)
    if schema != pinned_schema:
        raise ValueError(
            f"Stage1 provenance schema {schema!r} does not match pinned compiler schema {pinned_schema!r}"
        )
    if source_revision != pinned_revision:
        raise ValueError(
            f"stage1/frontend provenance mismatch: stage1={source_revision} "
            f"frontend={pinned_revision}"
        )
    expected_tree = committed_compiler_source_digest(frontend_repo, pinned_revision)
    if source_tree != expected_tree:
        raise ValueError("stage1/frontend provenance mismatch: source-tree digest differs from pinned frontend")
    expected_recipe = committed_compiler_recipe_digest(frontend_repo, pinned_revision)
    if build_recipe != expected_recipe:
        raise ValueError("stage1/frontend provenance mismatch: build-recipe digest differs from pinned frontend")
    if schema == "elisa-stage1-provenance-v5":
        validate_stage1_v5_shape(provenance)
        verify_stage1_v5_exact_inputs(product, compiler_root, frontend_repo, pinned_revision)
        if pinned_stage0_revision:
            verify_stage1_v5_seed_chain(
                product, provenance, frontend_repo, pinned_stage0_revision,
                seen_products if seen_products is not None else set(),
            )
        elif require_stage0_binding:
            raise ValueError("Stage1 v5 qualification requires the exact ELISA_STAGE0_REV pin")
    elif require_stage0_binding:
        raise ValueError("Stage1 provenance does not record a verifiable Stage0 seed chain")

    if compiler_root:
        snapshot_path = os.path.join(compiler_root, "SNAPSHOT")
        if os.path.isfile(snapshot_path):
            snapshot_values = {}
            with open(snapshot_path, encoding="utf-8") as handle:
                for line in handle:
                    key, separator, value = line.partition(":")
                    if separator:
                        snapshot_values[key.strip()] = value.strip()
            snapshot_revision = (snapshot_values.get("source_revision")
                                 or snapshot_values.get("revision"))
            if not snapshot_revision or not pinned_revision.startswith(snapshot_revision):
                raise ValueError("Stage1 snapshot revision does not match the imported frontend pin")
            if source_revision != pinned_revision:
                raise ValueError("Stage1 product provenance does not match its installed snapshot")
        else:
            checkout_revision = git(compiler_root, "rev-parse", "--verify", "HEAD^{commit}")
            if not checkout_revision or source_revision != checkout_revision:
                raise ValueError("Stage1 product provenance does not match its source-worktree commit")
    return provenance


def stage1_provenance_revision(product: str, compiler_root: str,
                               frontend_repo: str, frontend_revision: str,
                               *, pinned_stage0_revision: str = "",
                               require_stage0_binding: bool = False) -> str:
    """Return Stage1's source revision only after validating its full provenance."""
    return validated_stage1_provenance(
        product, compiler_root, frontend_repo, frontend_revision,
        pinned_stage0_revision=pinned_stage0_revision,
        require_stage0_binding=require_stage0_binding,
    )["source_revision"]


def stage1_source_tree_digest(root: str) -> str:
    """Hash the Stage1 frontend and stdlib using its provenance algorithm."""
    root_path = Path(root).resolve()
    files = []
    for directory in ("src", "elisacore_std"):
        base = root_path / directory
        if not base.is_dir() or base.is_symlink():
            raise ValueError(f"compiler snapshot is missing a regular {directory} directory")
        files.extend(candidate for candidate in base.rglob("*") if candidate.is_file())
    digest = hashlib.sha256()
    for path in sorted(set(files), key=lambda value: value.relative_to(root_path).as_posix()):
        digest.update(path.relative_to(root_path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    if not files:
        raise ValueError("compiler snapshot has no source files")
    return digest.hexdigest()


def validated_stage1_snapshot_std_root(snapshot_root: str, product: str,
                                       compiler_root: str, frontend_repo: str,
                                       frontend_revision: str, *,
                                       pinned_stage0_revision: str = "",
                                       require_stage0_binding: bool = False) -> str:
    """Select snapshot stdlib only when its exact source tree matches Stage1 provenance."""
    provenance = validated_stage1_provenance(
        product, compiler_root, frontend_repo, frontend_revision,
        pinned_stage0_revision=pinned_stage0_revision,
        require_stage0_binding=require_stage0_binding,
    )
    root = os.path.realpath(snapshot_root)
    revision_path = os.path.join(root, ".rev")
    try:
        with open(revision_path, encoding="ascii") as handle:
            snapshot_revision = handle.read().strip()
    except OSError as error:
        raise ValueError(f"compiler snapshot revision is unavailable: {error}") from error
    if snapshot_revision != provenance["source_revision"]:
        raise ValueError("compiler snapshot revision differs from selected Stage1 provenance")
    if stage1_source_tree_digest(root) != provenance["source_tree_sha256"]:
        raise ValueError("compiler snapshot source tree differs from selected Stage1 provenance")
    return os.path.join(root, "elisacore_std")
