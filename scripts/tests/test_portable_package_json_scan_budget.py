"""Bound nested JSON member-count rescans before the package DOM is allocated."""

import copy
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from portable_replay_support import BINARY as PROOF, REPLAY, TRUST


PARSER_DEPTH_LIMIT = 256
INPUT_FILE_LIMIT_BYTES = 64 * 1024 * 1024
CONTAINER_SCAN_FACTOR = 8
SCAN_WORK_BUDGET_BYTES = INPUT_FILE_LIMIT_BYTES * CONTAINER_SCAN_FACTOR
CPU_LIMIT_SECONDS = 4
WALL_LIMIT_SECONDS = 5
RSS_LIMIT_BYTES = 512 * 1024 * 1024
OUTPUT_LIMIT_BYTES = 16 * 1024


def limit_child_cpu():
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT_SECONDS, CPU_LIMIT_SECONDS))


def sample_rss(pid):
    sampled = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(pid)],
                             capture_output=True, text=True, check=False, timeout=1)
    try:
        return int(sampled.stdout.strip()) * 1024
    except ValueError:
        return 0


def replay_bytes(payload, path):
    path.write_bytes(payload)
    stdout_path = path.with_suffix(path.suffix + ".stdout")
    stderr_path = path.with_suffix(path.suffix + ".stderr")
    started = time.monotonic()
    with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
        child = subprocess.Popen([str(REPLAY), str(path)], stdout=stdout_file, stderr=stderr_file,
                                 preexec_fn=limit_child_cpu)
        peak_rss = 0
        while child.poll() is None:
            elapsed = time.monotonic() - started
            peak_rss = max(peak_rss, sample_rss(child.pid))
            output_bytes = stdout_path.stat().st_size + stderr_path.stat().st_size
            if elapsed >= WALL_LIMIT_SECONDS or peak_rss > RSS_LIMIT_BYTES \
                    or output_bytes > OUTPUT_LIMIT_BYTES:
                child.kill()
                child.wait()
                raise AssertionError(("bounded package replay exceeded a resource limit",
                                      path.name, elapsed, peak_rss, output_bytes))
            time.sleep(0.01)
        returncode = child.wait()
    elapsed = time.monotonic() - started
    output_bytes = stdout_path.stat().st_size + stderr_path.stat().st_size
    assert elapsed < WALL_LIMIT_SECONDS and peak_rss <= RSS_LIMIT_BYTES \
        and output_bytes <= OUTPUT_LIMIT_BYTES, (path.name, elapsed, peak_rss, output_bytes)
    assert returncode in (0, 1), (path.name, returncode, stderr_path.read_bytes())
    result = json.loads(stdout_path.read_bytes())
    assert result.get("format") == "elisa-proof-replay-result-v1", (path.name, result)
    assert result.get("trust") == TRUST, (path.name, result)
    return returncode, result


def assert_no_publication(code, result, status, reason):
    assert code == 1 and result.get("status") == status and result.get("reason") == reason, result
    assert result.get("theorems") == [], result
    assert result.get("summary") == {"theorems": 0, "replayed": 0, "not_replayed": 0}, result


def nested_string(depth, total_bytes=None):
    prefix = b"[" * depth + b'"'
    suffix = b'"' + b"]" * depth
    if total_bytes is None:
        total_bytes = len(prefix) + len(suffix) + 1
    padding = total_bytes - len(prefix) - len(suffix)
    assert padding >= 0, (depth, total_bytes)
    return prefix + b"x" * padding + suffix


def main():
    exported = subprocess.run(
        [str(PROOF), "--package", str(ROOT / "examples/verified.elisa")],
        capture_output=True, text=True, timeout=120,
    )
    assert exported.returncode == 0, (exported.returncode, exported.stderr)
    package = json.loads(exported.stdout)
    assert package["theorems"], "positive package must contain replayable theorems"

    with tempfile.TemporaryDirectory(prefix="elisa-proof-json-scan-budget-") as directory:
        work = Path(directory)

        # A positive package is always checked in a new replay process against the selected pair.
        positive_path = work / "positive.json"
        positive_path.write_text(json.dumps(package, separators=(",", ":")), encoding="utf-8")
        positive_code, positive = replay_bytes(positive_path.read_bytes(), positive_path)
        assert positive_code == 0 and positive["status"] == "replayed", positive
        assert positive["summary"] == {
            "theorems": len(package["theorems"]),
            "replayed": len(package["theorems"]),
            "not_replayed": 0,
        }, positive

        # Token-like punctuation, exponent text, and escaped quotes inside strings must not be
        # treated as JSON structure or numeric tokens by the single-pass preflight.
        escaped = copy.deepcopy(package)
        escaped["source"]["path"] = 'markers [] {} , : -1.25e+9 "quoted" \\ tail'
        escaped_code, escaped_result = replay_bytes(
            json.dumps(escaped, separators=(",", ":"), ensure_ascii=True).encode(),
            work / "escaped-punctuation.json",
        )
        assert escaped_code == 0 and escaped_result["status"] == "replayed", escaped_result
        assert escaped_result["summary"]["not_replayed"] == 0, escaped_result

        # Broad shallow containers stay within the scan budget and reach ordinary schema
        # validation; their immediate member count does not cause a depth-based false refusal.
        wide_array = b"[" + b",".join([b"0"] * 32768) + b"]"
        code, array_result = replay_bytes(wide_array, work / "wide-array.json")
        assert_no_publication(code, array_result, "malformed", "package-schema")
        wide_object = b"{" + b",".join(
            (b'"k' + str(index).encode("ascii") + b'":0') for index in range(12000)
        ) + b"}"
        code, object_result = replay_bytes(wide_object, work / "wide-object.json")
        assert_no_publication(code, object_result, "malformed", "package-schema")

        # The parser's exact depth boundary remains usable for short JSON, and the one-over
        # document still receives the parser's structured malformed-JSON result.
        code, exact_depth = replay_bytes(nested_string(PARSER_DEPTH_LIMIT), work / "depth-exact.json")
        assert_no_publication(code, exact_depth, "malformed", "package-schema")
        code, over_depth = replay_bytes(nested_string(PARSER_DEPTH_LIMIT + 1), work / "depth-over.json")
        assert_no_publication(code, over_depth, "malformed", "json")

        # The parser's repeated member-count scans are conservatively bounded by maximum depth
        # times input bytes. Exact work is admitted; one byte over is refused before DOM parsing.
        exact_scan_size = SCAN_WORK_BUDGET_BYTES // PARSER_DEPTH_LIMIT
        exact_scan = nested_string(PARSER_DEPTH_LIMIT, exact_scan_size)
        code, exact_scan_result = replay_bytes(exact_scan, work / "scan-exact.json")
        assert_no_publication(code, exact_scan_result, "malformed", "package-schema")
        over_scan = nested_string(PARSER_DEPTH_LIMIT, exact_scan_size + 1)
        code, over_scan_result = replay_bytes(over_scan, work / "scan-over.json")
        assert_no_publication(code, over_scan_result, "over-budget", "json-scan-budget")

        malformed = b'{"format":'
        code, malformed_result = replay_bytes(malformed, work / "malformed.json")
        assert_no_publication(code, malformed_result, "malformed", "json")

        rejected_package = copy.deepcopy(package)
        rejected_package["source"]["admissible"] = False
        code, rejected_result = replay_bytes(
            json.dumps(rejected_package, separators=(",", ":")).encode(),
            work / "source-inadmissible.json",
        )
        assert_no_publication(code, rejected_result, "rejected", "source-inadmissible")


if __name__ == "__main__":
    main()
    print("portable package JSON scan budget: exact/one-over work, broad containers, escaped-token "
          "strings, malformed/rejected outcomes, bounded resources, and fresh replay verified")
