"""Hash census input bytes and the textual include dependencies the checker reads."""
import hashlib
import os
from pathlib import Path
import re

# Mirrors proof_include_path: ordinary directives require a literal space after
# include and a double-quoted argument; brace directives are case insensitive.
ORDINARY = re.compile(r'^#?\s*include +\s*"(.*)"$', re.ASCII)
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
    pending = [Path(os.path.abspath(path)) for path in paths]
    visited = set()
    files = {}
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
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
                pending.append(Path(os.path.abspath(path.parent / raw_path)))
    digest = hashlib.sha256()
    for path, identity in sorted(files.items()):
        digest.update(os.fsencode(path) + b"\0")
        if "sha256" in identity:
            digest.update(b"file\0" + identity["sha256"].encode())
        else:
            digest.update(b"missing\0" + str(identity["read_error"]).encode())
        digest.update(b"\0")
    return {"sha256": digest.hexdigest(), "files": files}
