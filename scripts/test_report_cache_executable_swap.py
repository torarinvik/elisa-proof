#!/usr/bin/env python3
"""Ensure replacing a real verifier at one path invalidates its cached report."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORT_CACHE_SPEC = importlib.util.spec_from_file_location(
    "report_cache_executable_swap", ROOT / "scripts/report_cache.py"
)
assert REPORT_CACHE_SPEC and REPORT_CACHE_SPEC.loader
report_cache = importlib.util.module_from_spec(REPORT_CACHE_SPEC)
REPORT_CACHE_SPEC.loader.exec_module(report_cache)
PREFETCH_SPEC = importlib.util.spec_from_file_location(
    "prefetch_reports_executable_swap", ROOT / "scripts/prefetch_reports.py"
)
assert PREFETCH_SPEC and PREFETCH_SPEC.loader
prefetch = importlib.util.module_from_spec(PREFETCH_SPEC)
PREFETCH_SPEC.loader.exec_module(prefetch)

SOURCE_BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof")).resolve()
FIXTURE = ROOT / "examples/perf_luna_accept.elisa"


def main() -> None:
    assert SOURCE_BINARY.is_file() and os.access(SOURCE_BINARY, os.X_OK), SOURCE_BINARY
    previous_default_binary = report_cache.DEFAULT_BINARY
    previous_cache = os.environ.get("ELISA_PROOF_REPORT_CACHE")
    try:
        with tempfile.TemporaryDirectory(prefix="elisa-report-cache-executable-swap-") as temporary:
            directory = Path(temporary)
            executable = directory / "elisa-proof"
            cache_dir = directory / "reports"
            cache_dir.mkdir()
            (cache_dir / "pending").mkdir()
            shutil.copy2(SOURCE_BINARY, executable)
            executable.chmod(executable.stat().st_mode | 0o111)
            report_cache.DEFAULT_BINARY = executable
            os.environ["ELISA_PROOF_REPORT_CACHE"] = str(cache_dir)

            prefetch.run_one(str(executable), str(cache_dir), str(FIXTURE))
            original_key = report_cache.cache_key(FIXTURE, executable)
            original = report_cache._read_cached_entry(str(cache_dir / original_key))
            assert original is not None, "initial real verifier did not publish a valid report"

            # Appending inert trailing bytes creates a distinct executable product at the same
            # path while preserving the actual verifier and its report behavior.
            with executable.open("ab") as handle:
                handle.write(b"\nreport-cache-same-path-replacement\n")
            replacement_key = report_cache.cache_key(FIXTURE, executable)
            assert replacement_key != original_key, "same-path executable replacement kept its cache key"

            original_run = report_cache.subprocess.run
            invocations = []

            def count_verifier_invocations(*args, **kwargs):
                invocations.append(args[0])
                return original_run(*args, **kwargs)

            report_cache.subprocess.run = count_verifier_invocations
            try:
                prefetch.run_one(str(executable), str(cache_dir), str(FIXTURE))
            finally:
                report_cache.subprocess.run = original_run
            assert len(invocations) == 1, (
                "replacement cache miss must launch exactly one fresh verifier invocation",
                len(invocations),
            )
            replaced = report_cache._read_cached_entry(str(cache_dir / replacement_key))
            assert replaced is not None, "replacement verifier did not publish a valid report"
            assert replaced[0] == 0 and json.loads(replaced[1]).get("status") == "proved"

            # The second lookup must hit the newly written entry without another verifier call.
            def fail_if_cached_lookup_runs(*args, **kwargs):
                raise AssertionError("valid replacement report unexpectedly missed the cache")

            report_cache.subprocess.run = fail_if_cached_lookup_runs
            try:
                cached = report_cache.json_run(FIXTURE, executable, timeout=120)
            finally:
                report_cache.subprocess.run = original_run
            assert cached == replaced, "replacement report was not served from cache"

            os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
            try:
                uncached = report_cache.json_run(FIXTURE, executable, timeout=120)
            finally:
                os.environ["ELISA_PROOF_REPORT_CACHE"] = str(cache_dir)
            assert cached == uncached, "replacement cache report differs from uncached CLI output"
            print(
                f"real executable replacement: {original_key[:12]} -> {replacement_key[:12]}, "
                "one fresh invocation, cached and uncached reports equal"
            )
    finally:
        report_cache.DEFAULT_BINARY = previous_default_binary
        if previous_cache is None:
            os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
        else:
            os.environ["ELISA_PROOF_REPORT_CACHE"] = previous_cache


if __name__ == "__main__":
    main()
