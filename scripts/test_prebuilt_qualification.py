"""Reject stale source and compiler identities in the prebuilt-test gate."""

from copy import deepcopy
import io
import os
from pathlib import Path
import tarfile
import tempfile

from prebuilt_qualification import (
    validate_compiler_snapshot_tree, validate_frontend_metadata, validate_source_metadata,
    validate_stage0_build_info,
)


def manifest(stage="stage1"):
    return {
        "proof": {
            "head": "a" * 40,
            "source_dirty": False,
            "source_tree_sha256": "",
        },
        "frontend": {"revision": "b" * 40, "tree": "e" * 40},
        "compiler": {
            "stage": stage,
            "stage1_revision": "b" * 40 if stage == "stage1" else None,
            "source_revision": "b" * 40 if stage == "stage1" else "c" * 40,
            "source_dirty": False,
        },
    }


with tempfile.TemporaryDirectory(prefix="elisa-prebuilt-qualification-") as directory:
    root = Path(directory)
    source = root / "proof-src"
    snapshot = root / "snapshot-src"
    source.mkdir()
    snapshot.mkdir()
    (source / "main.elisa").write_text("def valid() -> bool: return true\n")
    (snapshot / "main.elisa").write_bytes((source / "main.elisa").read_bytes())
    proof_manifest = manifest()

    from build_manifest_hashes import tree_digest

    proof_manifest["proof"]["source_tree_sha256"] = tree_digest(str(source))
    pair = {"elisa-proof": proof_manifest, "elisa-proof-replay": deepcopy(proof_manifest)}
    digest = validate_source_metadata(pair, source, snapshot, "a" * 40, False)
    assert digest == proof_manifest["proof"]["source_tree_sha256"]
    assert validate_frontend_metadata(pair, "b" * 40, "b" * 40, "c" * 40, "e" * 40) == "stage1"

    source_link = source / "linked.elisa"
    source_link.symlink_to("main.elisa")
    try:
        validate_source_metadata(pair, source, snapshot, "a" * 40, False)
    except ValueError as error:
        assert "non-regular file" in str(error)
    else:
        raise AssertionError("prebuilt gate followed a proof-source file symlink")
    source_link.unlink()

    snapshot_link_directory = snapshot / "linked-dir"
    snapshot_link_directory.symlink_to(source, target_is_directory=True)
    try:
        validate_source_metadata(pair, source, snapshot, "a" * 40, False)
    except ValueError as error:
        assert "non-directory entry" in str(error)
    else:
        raise AssertionError("prebuilt gate ignored a proof-source symlinked directory")
    snapshot_link_directory.unlink()

    stale_source = deepcopy(pair)
    stale_source["elisa-proof-replay"]["proof"]["source_tree_sha256"] = "f" * 64
    try:
        validate_source_metadata(stale_source, source, snapshot, "a" * 40, False)
    except ValueError as error:
        assert "does not match the current proof source tree" in str(error)
    else:
        raise AssertionError("prebuilt gate accepted a binary built from a stale proof source tree")

    stale_cleanliness = deepcopy(pair)
    stale_cleanliness["elisa-proof-replay"]["proof"]["source_dirty"] = True
    try:
        validate_source_metadata(stale_cleanliness, source, snapshot, "a" * 40, False)
    except ValueError as error:
        assert "cleanliness metadata" in str(error)
    else:
        raise AssertionError("prebuilt gate accepted stale proof-source cleanliness metadata")

    (snapshot / "main.elisa").write_text("def stale() -> bool: return false\n")
    try:
        validate_source_metadata(pair, source, snapshot, "a" * 40, False)
    except ValueError as error:
        assert "snapshot source differs" in str(error)
    else:
        raise AssertionError("prebuilt gate accepted a compiler snapshot with different proof source")

    (snapshot / "main.elisa").write_bytes((source / "main.elisa").read_bytes())
    wrong_head = deepcopy(pair)
    wrong_head["elisa-proof-replay"]["proof"]["head"] = "d" * 40
    try:
        validate_source_metadata(wrong_head, source, snapshot, "a" * 40, False)
    except ValueError as error:
        assert "different proof HEAD" in str(error)
    else:
        raise AssertionError("prebuilt gate accepted a product built from another proof HEAD")

    wrong_frontend = deepcopy(pair)
    wrong_frontend["elisa-proof-replay"]["compiler"]["stage1_revision"] = "e" * 40
    try:
        validate_frontend_metadata(wrong_frontend, "b" * 40, "b" * 40, "c" * 40, "e" * 40)
    except ValueError as error:
        assert "Stage1 product" in str(error)
    else:
        raise AssertionError("prebuilt gate accepted a Stage1 product from another frontend")

    wrong_frontend_tree = deepcopy(pair)
    wrong_frontend_tree["elisa-proof-replay"]["frontend"]["tree"] = "f" * 40
    try:
        validate_frontend_metadata(wrong_frontend_tree, "b" * 40, "b" * 40, "c" * 40, "e" * 40)
    except ValueError as error:
        assert "frontend source tree" in str(error)
    else:
        raise AssertionError("prebuilt gate accepted a product from a different compiler source tree")

    compiler_snapshot = root / "compiler-snapshot"
    compiler_files = {
        "src/parser/parser.elisa": b"def parse() -> bool: return true\n",
        "elisacore_std/prelude.elisa": b"const VERSION: u32 = 1\n",
        "test/parity/profile_hooks.c": b"void profiler_hook(void) {}\n",
    }
    for relative, contents in compiler_files.items():
        destination = compiler_snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(contents)
    revision_marker = "b" * 40
    (compiler_snapshot / ".rev").write_text(revision_marker + "\n", encoding="ascii")
    archive_buffer = io.BytesIO()
    with tarfile.open(fileobj=archive_buffer, mode="w:") as archive:
        for relative, contents in compiler_files.items():
            member = tarfile.TarInfo(relative)
            member.size = len(contents)
            archive.addfile(member, io.BytesIO(contents))
    compiler_archive = archive_buffer.getvalue()
    compiler_tree = validate_compiler_snapshot_tree(compiler_snapshot, compiler_archive)
    assert len(compiler_tree) == 64

    if os.name != "nt":
        linked_snapshot = root / "compiler-snapshot-link"
        linked_snapshot.symlink_to(compiler_snapshot, target_is_directory=True)
        try:
            validate_compiler_snapshot_tree(linked_snapshot, compiler_archive)
        except ValueError as error:
            assert "not a regular directory" in str(error)
        else:
            raise AssertionError("prebuilt gate accepted a symlinked compiler snapshot root")

    # Keep the same revision marker while altering the source file itself. A .rev-only
    # check would miss this stale/tampered snapshot.
    (compiler_snapshot / "src/parser/parser.elisa").write_bytes(b"def parse() -> bool: return false\n")
    try:
        validate_compiler_snapshot_tree(compiler_snapshot, compiler_archive)
    except ValueError as error:
        assert "differs from pinned Git archive" in str(error)
    else:
        raise AssertionError("prebuilt gate accepted modified compiler files with an unchanged .rev")
    assert (compiler_snapshot / ".rev").read_text(encoding="ascii").strip() == revision_marker

    (compiler_snapshot / "src/parser/parser.elisa").write_bytes(compiler_files["src/parser/parser.elisa"])
    (compiler_snapshot / "unexpected.elisa").write_text("stale", encoding="utf-8")
    try:
        validate_compiler_snapshot_tree(compiler_snapshot, compiler_archive)
    except ValueError as error:
        assert "file set differs" in str(error)
    else:
        raise AssertionError("prebuilt gate accepted extra compiler snapshot files")
    (compiler_snapshot / "unexpected.elisa").unlink()

    stage0_pair = {role: deepcopy(value) for role, value in pair.items()}
    for value in stage0_pair.values():
        value["compiler"] = {
            "stage": "stage0", "stage1_revision": None,
            "source_revision": "c" * 40, "source_dirty": False,
        }
    assert validate_frontend_metadata(stage0_pair, "b" * 40, "b" * 40, "c" * 40, "e" * 40) == "stage0"
    for value in stage0_pair.values():
        value["compiler"]["source_revision"] = None
        value["compiler"]["source_dirty"] = None
    assert validate_frontend_metadata(stage0_pair, "b" * 40, "b" * 40, "c" * 40, "e" * 40) == "stage0"
    stage0_pair["elisa-proof"]["compiler"]["source_revision"] = "d" * 40
    try:
        validate_frontend_metadata(stage0_pair, "b" * 40, "b" * 40, "c" * 40, "e" * 40)
    except ValueError as error:
        assert "Stage0 source revision" in str(error)
    else:
        raise AssertionError("prebuilt gate accepted a Stage0 product from another source revision")

    assert validate_stage0_build_info(
        "elisa: devel\n\tbuild\tvcs.revision=" + "c" * 40 +
        "\n\tbuild\tvcs.modified=false\n", "c" * 40,
    ) == "c" * 40
    try:
        validate_stage0_build_info(
            "\tbuild\tvcs.revision=" + "c" * 40 + "\n\tbuild\tvcs.modified=true\n",
            "c" * 40,
        )
    except ValueError as error:
        assert "modified sources" in str(error)
    else:
        raise AssertionError("prebuilt gate accepted a Stage0 binary built from dirty sources")

print("prebuilt qualification: exact proof/compiler snapshots, pins, and Stage0/Stage1 provenance are enforced")
