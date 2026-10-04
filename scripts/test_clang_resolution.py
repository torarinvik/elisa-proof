"""Native tool overrides are exact, quoted, and shared by compilation and linking."""
import os
from pathlib import Path
import subprocess
import tempfile

if not __debug__:
    raise SystemExit("clang selection checks must run without Python -O")
ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/link_flags.sh"

with tempfile.TemporaryDirectory(prefix="elisa-clang-selection-") as temporary:
    root = Path(temporary)
    tools = root / "tool chain"
    tools.mkdir()
    clang = tools / "clang"
    config = tools / "llvm-config"
    clang.write_text("#!/bin/sh\nprintf 'selected tool\\n'\nprintf '%s\\n' \"$@\"\n")
    config.write_text("#!/bin/sh\nexit 0\n")
    clang.chmod(0o755)
    config.chmod(0o755)
    environment = dict(os.environ)
    for name in ("ELISA_CLANG", "LLVM_CONFIG", "ELISA_LLVM_BIN_DIR"):
        environment.pop(name, None)

    def run(overrides, command="elisa_resolve_clang"):
        return subprocess.run(["bash", "-c", 'source "$1"; ' + command, "probe", str(HELPER), str(root)],
                              env=dict(environment, **overrides), capture_output=True,
                              text=True, timeout=10)

    for overrides in ({"ELISA_CLANG": str(clang)},
                      {"LLVM_CONFIG": str(config)},
                      {"ELISA_LLVM_BIN_DIR": str(tools)},
                      {"ELISA_CLANG": str(clang), "LLVM_CONFIG": str(root / "missing")},
                      {"LLVM_CONFIG": "llvm-config", "PATH": str(tools) + os.pathsep + environment["PATH"]}):
        result = run(overrides)
        assert result.returncode == 0 and result.stdout == str(clang) + "\n", result
        assert result.stderr == "", result.stderr
        result = run(overrides, 'elisa_clang "argument with spaces" --version')
        assert result.returncode == 0, result.stderr
        assert result.stdout == "selected tool\nargument with spaces\n--version\n", result.stdout
        result = run(overrides, 'elisa_link_native "$2" "argument with spaces" --version')
        assert result.returncode == 0, result.stderr
        assert result.stdout == "selected tool\nargument with spaces\n--version\n", result.stdout

    for overrides in ({"ELISA_CLANG": str(root / "missing")},
                      {"ELISA_LLVM_BIN_DIR": str(root / "missing")},
                      {"LLVM_CONFIG": str(root / "missing")}):
        result = run(overrides)
        assert result.returncode == 2 and result.stdout == "", result
        assert result.stderr, result

    # A file's existence is not enough: explicit non-executable tools are refused.
    clang.chmod(0o644)
    result = run({"ELISA_CLANG": str(clang)})
    assert result.returncode == 2 and result.stdout == "", result

print("clang selection: explicit LLVM tools honored; quoted arguments retained; invalid overrides refused")
