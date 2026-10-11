"""Digest helpers shared by the proof build identity and snapshot tools."""

import hashlib
import json
import os
import re
from compiler_environment import select_compiler_environment

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
