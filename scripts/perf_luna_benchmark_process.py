"""Process isolation and timeout controls for the Luna benchmark."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from perf_build_provenance import file_identity, require_compatible_products
from perf_luna_benchmark_validation import measurement_self_test


def require_unchanged_inputs(identities: dict[Path, dict]) -> None:
    for path, identity in identities.items():
        if file_identity(path) != identity:
            raise RuntimeError(f"benchmark input changed during measurement: {path}")


def run_wrapper(wrapper: list[str], timeout: float) -> subprocess.CompletedProcess:
    """Run a measurement wrapper in its own process group and reap it on timeout."""
    process = subprocess.Popen(wrapper, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        raise RuntimeError(f"measurement wrapper timed out after {timeout}s: {stderr.strip()}") from error
    return subprocess.CompletedProcess(wrapper, process.returncode, stdout, stderr)


def process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                               capture_output=True, text=True, check=False).stdout.strip()
    except OSError:
        return True
    return bool(state) and not state.startswith("Z")


def self_test_process_group_cleanup(entrypoint: Path) -> None:
    """Check output preservation and ensure a watchdog kills descendant processes."""
    ordinary_command = [sys.executable, str(entrypoint), "_measure",
                        json.dumps([sys.executable, "-c", "print('ordinary')"],
                                   separators=(",", ":"))]
    ordinary = run_wrapper(ordinary_command, 5)
    if ordinary.returncode != 0:
        raise RuntimeError(f"ordinary measurement failed: {ordinary.stderr.strip()}")
    try:
        measured = json.loads(ordinary.stdout)
        ordinary_stdout = base64.b64decode(measured["stdout"], validate=True)
    except (ValueError, KeyError) as error:
        raise RuntimeError("ordinary measurement returned invalid output") from error
    if measured.get("returncode") != 0 or ordinary_stdout != b"ordinary\n":
        raise RuntimeError("ordinary measurement did not preserve its successful command output")
    if (not isinstance(measured.get("wall_seconds"), (int, float))
            or not isinstance(measured.get("user_cpu_seconds"), (int, float))
            or not isinstance(measured.get("system_cpu_seconds"), (int, float))
            or measured.get("peak_rss_kib") is not None
            and not isinstance(measured.get("peak_rss_kib"), int)):
        raise RuntimeError("measurement wrapper returned invalid per-process resource metrics")

    coherent_manifest = {
        "proof": {"source_tree_sha256": "source", "source_dirty": False},
        "frontend": {"revision": "frontend", "tree": "frontend-tree"},
        "compiler": {"stage": "stage1", "stage1_revision": "stage1", "source_revision": "compiler-rev",
                     "source_dirty": False, "product": {"sha256": "compiler"},
                     "executable": {"sha256": "driver"}},
        "runtime": {"sha256": "runtime"},
        "profile_hooks": {"sha256": "hooks"},
        "target": "arm64-fixture", "optimization": "O2", "compile_mode": "strict",
        "compiler_flags": ["-emit", "obj", "-O2"],
    }
    require_compatible_products(coherent_manifest, coherent_manifest, "fixture")
    measurement_self_test()
    mismatched_manifest = dict(coherent_manifest)
    mismatched_manifest["frontend"] = {"revision": "stale-frontend", "tree": "stale-tree"}
    try:
        require_compatible_products(coherent_manifest, mismatched_manifest, "fixture")
    except RuntimeError as error:
        if "frontend" not in str(error):
            raise
    else:
        raise RuntimeError("proof/replay products with different frontend revisions were accepted")

    with tempfile.TemporaryDirectory(prefix="elisa-perf-luna-self-test-") as temporary:
        directory = Path(temporary)
        stable = directory / "identity-control"
        stable.write_bytes(b"stable input")
        identities = {stable: file_identity(stable)}
        if identities[stable] != {"sha256": hashlib.sha256(b"stable input").hexdigest(),
                                  "size_bytes": len(b"stable input")}:
            raise RuntimeError("benchmark input identity is incorrect")
        require_unchanged_inputs(identities)
        stable.write_bytes(b"mutated input")
        try:
            require_unchanged_inputs(identities)
        except RuntimeError as error:
            if "input changed" not in str(error):
                raise
        else:
            raise RuntimeError("benchmark input mutation was not refused")
        target = directory / "fake-proof"
        pid_file = directory / "child.pid"
        target.write_text(
            "#!/usr/bin/env python3\n"
            "import subprocess, sys, time\n"
            "child = subprocess.Popen(['sleep', '60'])\n"
            "open(sys.argv[1], 'w').write(str(child.pid))\n"
            "time.sleep(60)\n",
            encoding="utf-8",
        )
        target.chmod(0o755)
        command = [sys.executable, str(entrypoint), "_measure",
                   json.dumps([str(target), str(pid_file)], separators=(",", ":"))]
        try:
            run_wrapper(command, 2)
        except RuntimeError as error:
            if "timed out" not in str(error):
                raise
        else:
            raise RuntimeError("watchdog did not time out the sleeping fake executable")
        if not pid_file.exists():
            raise RuntimeError("fake executable did not start its child before timeout")
        child_pid = int(pid_file.read_text(encoding="utf-8"))
        deadline = time.monotonic() + 3
        while process_is_running(child_pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        if process_is_running(child_pid):
            raise RuntimeError(f"target child {child_pid} survived process-group cleanup")
