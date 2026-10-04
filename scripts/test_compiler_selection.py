"""Explicit compiler checkouts take precedence over unrelated PATH products."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

if not __debug__:
    raise SystemExit("compiler selection checks must run without Python -O")
ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
assert BASH
with tempfile.TemporaryDirectory(prefix="elisa-compiler-selection-") as directory:
    scratch = Path(directory).resolve()
    path_bin = scratch / "path"
    path_bin.mkdir()
    path_product = path_bin / "elisac-stage1"
    path_product.write_text("#!/bin/sh\nexit 0\n")
    path_product.chmod(0o755)
    checkouts = []
    for name in ("source checkout", "root checkout"):
        checkout = scratch / name
        wrapper = checkout / "scripts/elisac_stage1.sh"
        wrapper.parent.mkdir(parents=True)
        wrapper.write_text("#!/bin/sh\nexit 0\n")
        wrapper.chmod(0o755)
        checkouts.append(checkout)
    environment = {key: value for key, value in os.environ.items()
                   if key not in ("ELISA_COMPILER_ROOT", "ELISA_COMPILER_SRC")}
    environment["PATH"] = str(path_bin)
    def select(overrides):
        return subprocess.run(
            [BASH, "-c", 'source "$1"; elisa_default_stage1 "$2"',
             "compiler-selection", str(ROOT / "scripts/compiler_provenance.sh"), str(scratch / "proof")],
            env=dict(environment, **overrides), capture_output=True, text=True, timeout=10)
    default = select({})
    assert default.returncode == 0 and default.stdout.strip() == str(path_product), default
    source = select({"ELISA_COMPILER_SRC": str(checkouts[0])})
    assert source.returncode == 0 and source.stdout.strip() == str(checkouts[0] / "scripts/elisac_stage1.sh"), source
    preferred = select({"ELISA_COMPILER_SRC": str(checkouts[0]), "ELISA_COMPILER_ROOT": str(checkouts[1])})
    assert preferred.returncode == 0 and preferred.stdout.strip() == str(checkouts[1] / "scripts/elisac_stage1.sh"), preferred
    for variable in ("ELISA_COMPILER_SRC", "ELISA_COMPILER_ROOT"):
        missing = scratch / "missing"
        refused = select({variable: str(missing)})
        assert refused.returncode == 2 and refused.stdout == "", refused
        assert refused.stderr == "Stage1 wrapper not executable: %s/scripts/elisac_stage1.sh\n" % missing, refused
print("compiler selection: checkout overrides honored; missing explicit checkout cannot fall back to PATH")
