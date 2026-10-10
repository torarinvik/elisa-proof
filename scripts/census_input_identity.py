"""Hash census input bytes and the textual include dependencies the checker reads."""
from collections import deque
import hashlib
import os
from pathlib import Path
import re

# Mirrors proof_include_path: ordinary directives require a literal space after
# include and a double-quoted argument; brace directives are case insensitive.
ORDINARY = re.compile(r'^#?\s*include +\s*"(.*)"$', re.ASCII)
INCLUDE_DEPTH_LIMIT = 64
DEPENDENCY_FILE_LIMIT = 65536
BRACED = re.compile(r'^\{\$\s*(include|i)\s+(.+)\}$', re.IGNORECASE | re.ASCII)


def include_argument(line):
    line = line.strip(" \t\n\v\f\r")
    match = BRACED.fullmatch(line)
    if match:
        argument = match[2].strip(" \t\n\v\f\r")
        if len(argument) >= 2 and argument[0] == argument[-1] and argument[0] in "\"'":
            return argument[1:-1]
        return argument if not any(character in " \t\n\v\f\r" for character in argument) else None
    match = ORDINARY.fullmatch(line)
    return match[1] if match else None


def input_identity(paths):
    """Return a deterministic closure digest, including missing dependencies.

    Missing includes remain census inputs with their normal failure behavior;
    adding/removing such a file changes this identity. Paths stay lexical, as in
    the proof import resolver, so includes through symlink directories resolve
    from the source argument's directory rather than the physical target's.
    """
    pending = deque((Path(os.path.abspath(path)), 0) for path in paths)
    visited = set()
    files = {}
    while pending:
        path, depth = pending.popleft()
        if path in visited:
            continue
        if len(visited) >= DEPENDENCY_FILE_LIMIT:
            raise RuntimeError("census dependency identity exceeds its file budget")
        visited.add(path)
        if depth > INCLUDE_DEPTH_LIMIT:
            files[str(path)] = {"include_depth_limit": INCLUDE_DEPTH_LIMIT}
            continue
        try:
            contents = path.read_bytes()
        except OSError as error:
            files[str(path)] = {"read_error": error.errno}
            continue
        files[str(path)] = {"sha256": hashlib.sha256(contents).hexdigest()}
        # The importer scans byte lines, including directives inside source
        # strings. Latin-1 preserves every path byte without lossy replacement.
        for line in contents.split(b"\n"):
            argument = include_argument(line.decode("latin-1"))
            if argument is not None and "\0" not in argument:
                raw_path = os.fsdecode(argument.encode("latin-1"))
                pending.append((Path(os.path.abspath(path.parent / raw_path)), depth + 1))
    digest = hashlib.sha256()
    for path, identity in sorted(files.items()):
        digest.update(os.fsencode(path) + b"\0")
        if "sha256" in identity:
            digest.update(b"file\0" + identity["sha256"].encode())
        elif "read_error" in identity:
            digest.update(b"missing\0" + str(identity["read_error"]).encode())
        else:
            digest.update(b"depth-limit\0" + str(identity["include_depth_limit"]).encode())
        digest.update(b"\0")
    return {"sha256": digest.hexdigest(), "files": files}


def compiler_export_digest(root):
    """Use Stage1's source/stdlib digest format for a pinned compiler export."""
    paths = []
    for name in ("src", "elisacore_std"):
        directory = root / name
        if not directory.is_dir() or directory.is_symlink():
            raise RuntimeError(f"compiler snapshot directory is missing or linked: {directory}")
        for parent, directories, files in os.walk(directory):
            for child in directories + files:
                path = Path(parent) / child
                if path.is_symlink():
                    raise RuntimeError(f"compiler snapshot contains a symbolic link: {path}")
            paths.extend(Path(parent) / filename for filename in files)
    if not paths:
        raise RuntimeError("compiler snapshot has no source files")
    digest = hashlib.sha256()
    for path in sorted(paths):
        if not path.is_file():
            raise RuntimeError(f"compiler snapshot contains a non-file: {path}")
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1 << 20), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()
