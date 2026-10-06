"""Exact resource-boundary checks for portable-package JSON container rescans."""

import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from portable_replay_support import BINARY, REPLAY, TRUST


INPUT_LIMIT_BYTES = 64 * 1024 * 1024
SCAN_FACTOR = 8
PARSER_DEPTH_LIMIT = 256
SCAN_WORK_LIMIT = INPUT_LIMIT_BYTES * SCAN_FACTOR
SCAN_BYTE_LIMIT = SCAN_WORK_LIMIT // PARSER_DEPTH_LIMIT
CPU_LIMIT_SECONDS = 4
WALL_LIMIT_SECONDS = 8
RSS_LIMIT_BYTES = 512 * 1024 * 1024
OUTPUT_LIMIT_BYTES = 16 * 1024


def _cpu_limit():
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT_SECONDS, CPU_LIMIT_SECONDS))


def _rss_bytes(pid):
    result = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(pid)],
                            capture_output=True, text=True, check=False, timeout=1)
    try:
        return int(result.stdout.strip()) * 1024
    except ValueError:
        return 0


def _product_identity(binary):
    binary = Path(binary)
    manifest_path = Path(str(binary) + ".manifest.json")
    sidecar_path = Path(str(manifest_path) + ".sha256")
    manifest_bytes = manifest_path.read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == sidecar_path.read_text().strip(), manifest_path
    manifest = json.loads(manifest_bytes)
    assert manifest["schema"] == "elisa-proof-build-manifest-v1", manifest_path
    assert manifest["binary"]["sha256"] == hashlib.sha256(binary.read_bytes()).hexdigest(), binary
    return manifest


def _verify_pair():
    proof = _product_identity(BINARY)
    replay = _product_identity(REPLAY)
    assert proof["pair_generation"] == replay["pair_generation"], "pair generation mismatch"
    for field in ("frontend", "target", "optimization", "compile_mode", "proof", "compiler", "runtime"):
        assert proof[field] == replay[field], (field, proof[field], replay[field])
    assert proof["compiler"]["stage"] == "stage1", proof["compiler"]
    assert proof["compiler"]["source_dirty"] is False, proof["compiler"]
    assert proof["proof"]["source_dirty"] is False, proof["proof"]
    return proof


def _nested_string(total_bytes):
    prefix = b"[" * PARSER_DEPTH_LIMIT + b'"'
    suffix = b'"' + b"]" * PARSER_DEPTH_LIMIT
    padding = total_bytes - len(prefix) - len(suffix)
    assert padding >= 0
    return prefix + b"x" * padding + suffix


def _replay_fresh(raw, path):
    path.write_bytes(raw)
    stdout_path = path.with_suffix(".stdout")
    stderr_path = path.with_suffix(".stderr")
    started = time.monotonic()
    with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
        child = subprocess.Popen([str(REPLAY), str(path)], stdout=stdout_file,
                                 stderr=stderr_file, preexec_fn=_cpu_limit)
        peak_rss = 0
        while child.poll() is None:
            elapsed = time.monotonic() - started
            peak_rss = max(peak_rss, _rss_bytes(child.pid))
            output_size = stdout_path.stat().st_size + stderr_path.stat().st_size
            if elapsed >= WALL_LIMIT_SECONDS or peak_rss > RSS_LIMIT_BYTES \
                    or output_size > OUTPUT_LIMIT_BYTES:
                child.kill()
                child.wait()
                raise AssertionError(("replay exceeded boundary-test resource cap", path.name,
                                      elapsed, peak_rss, output_size))
            time.sleep(0.01)
        exit_code = child.wait()
    elapsed = time.monotonic() - started
    output_size = stdout_path.stat().st_size + stderr_path.stat().st_size
    assert elapsed < WALL_LIMIT_SECONDS and peak_rss <= RSS_LIMIT_BYTES \
        and output_size <= OUTPUT_LIMIT_BYTES, (path.name, elapsed, peak_rss, output_size)
    stdout = stdout_path.read_bytes()
    stderr = stderr_path.read_bytes()
    assert not stderr, (path.name, stderr[:512])
    result = json.loads(stdout)
    assert result.get("format") == "elisa-proof-replay-result-v1", (path.name, result)
    assert result.get("trust") == TRUST, (path.name, result)
    return exit_code, result


def _assert_refusal(exit_code, report, status, reason, label):
    assert exit_code == 1 and report.get("status") == status \
        and report.get("reason") == reason, (label, exit_code, report)
    assert report.get("theorems") == [], (label, report)
    assert report.get("summary") == {"theorems": 0, "replayed": 0, "not_replayed": 0}, (label, report)


def main():
    identity = _verify_pair()
    exported = subprocess.run([str(BINARY), "--package", str(ROOT / "examples/verified.elisa")],
                              capture_output=True, timeout=120)
    assert exported.returncode == 0, (exported.returncode, exported.stderr[:512])
    package = json.loads(exported.stdout)
    assert package.get("theorems"), "positive package must contain at least one theorem"

    with tempfile.TemporaryDirectory(prefix="elisa-proof-json-scan-boundary-") as directory:
        work = Path(directory)
        positive_code, positive = _replay_fresh(
            json.dumps(package, separators=(",", ":")).encode(), work / "positive.json")
        assert positive_code == 0 and positive.get("status") == "replayed", positive
        assert positive.get("summary") == {
            "theorems": len(package["theorems"]), "replayed": len(package["theorems"]),
            "not_replayed": 0,
        }, positive

        for label, size, expected_status, expected_reason in (
            ("cap-minus-one", SCAN_BYTE_LIMIT - 1, "malformed", "package-schema"),
            ("cap", SCAN_BYTE_LIMIT, "malformed", "package-schema"),
            ("cap-plus-one", SCAN_BYTE_LIMIT + 1, "over-budget", "json-scan-budget"),
        ):
            code, report = _replay_fresh(_nested_string(size), work / (label + ".json"))
            _assert_refusal(code, report, expected_status, expected_reason, label)

    proof = identity["proof"]
    compiler = identity["compiler"]
    print("portable package JSON scan boundary: cap-1/cap/cap+1 verified; "
          "positive replay and bounded fresh-process refusals passed; "
          "proof-source head=%s tree=%s; compiler stage=%s revision=%s" %
          (proof["head"], proof["source_tree_sha256"], compiler["stage"],
           compiler["source_revision"]))


if __name__ == "__main__":
    main()
