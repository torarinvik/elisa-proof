"""Snapshot refresh preserves byte-identical files and removes deleted inputs."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory(prefix="elisa-snapshot-preserve-") as directory:
    base = Path(directory)
    proof = base / "proof"
    compiler = base / "compiler"
    (proof / "scripts").mkdir(parents=True)
    (proof / "src").mkdir()
    (proof / "examples").mkdir()
    shutil.copy(ROOT / "scripts/compiler_snapshot.sh", proof / "scripts/compiler_snapshot.sh")
    stable = proof / "src/stable.elisa"
    stable.write_text("stable\n")
    stale = proof / "src/stale.elisa"
    stale.write_text("stale\n")
    (proof / "examples/example.elisa").write_text("example\n")

    compiler.mkdir()
    subprocess.run(["git", "init", "-q", str(compiler)], check=True)
    (compiler / "src").mkdir()
    (compiler / "elisacore_std").mkdir()
    (compiler / "test/parity").mkdir(parents=True)
    (compiler / "src/frontend.elisa").write_text("frontend\n")
    (compiler / "elisacore_std/std.elisa").write_text("std\n")
    (compiler / "test/parity/profile_hooks.c").write_text("void hook(void) {}\n")
    subprocess.run(["git", "-C", str(compiler), "add", "."], check=True)
    subprocess.run(["git", "-C", str(compiler), "-c", "user.name=Test", "-c",
                    "user.email=test@example.invalid", "commit", "-qm", "fixture"], check=True)
    revision = subprocess.check_output(["git", "-C", str(compiler), "rev-parse", "HEAD"], text=True).strip()
    env = dict(os.environ, ELISA_COMPILER_SRC=str(compiler), ELISA_COMPILER_REV=revision)
    runner = f'source "{proof}/scripts/compiler_snapshot.sh"'
    subprocess.run(["bash", "-c", runner], env=env, check=True)
    snap = proof / "build/snapshot/elisa-proof/src/stable.elisa"
    before = snap.stat()
    os.utime(stable, None)
    stale.unlink()
    (proof / "src/new.elisa").write_text("new\n")
    subprocess.run(["bash", "-c", runner], env=env, check=True)
    after = snap.stat()
    assert before.st_ino == after.st_ino
    assert snap.read_text() == "stable\n"
    assert not (proof / "build/snapshot/elisa-proof/src/stale.elisa").exists()
    assert (proof / "build/snapshot/elisa-proof/src/new.elisa").read_text() == "new\n"
print("compiler snapshot: unchanged files retain identity and deleted files are removed")
