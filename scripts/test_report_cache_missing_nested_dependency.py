#!/usr/bin/env python3
"""A newly appearing nested include must select a fresh real verifier report."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
REPORT_CACHE_SPEC = importlib.util.spec_from_file_location(
    "report_cache_missing_nested", ROOT / "scripts/report_cache.py"
)
assert REPORT_CACHE_SPEC and REPORT_CACHE_SPEC.loader
report_cache = importlib.util.module_from_spec(REPORT_CACHE_SPEC)
REPORT_CACHE_SPEC.loader.exec_module(report_cache)
PREFETCH_SPEC = importlib.util.spec_from_file_location(
    "prefetch_reports_missing_nested", ROOT / "scripts/prefetch_reports.py"
)
assert PREFETCH_SPEC and PREFETCH_SPEC.loader
prefetch = importlib.util.module_from_spec(PREFETCH_SPEC)
PREFETCH_SPEC.loader.exec_module(prefetch)

BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof")).resolve()


def cache_hit_without_runner(path: Path) -> tuple[int, str]:
    original_run = report_cache.subprocess.run
    try:
        def fail_if_cache_misses(*args, **kwargs):
            raise AssertionError("cache lookup unexpectedly launched the verifier")

        report_cache.subprocess.run = fail_if_cache_misses
        return report_cache.json_run(path, BINARY, timeout=120)
    finally:
        report_cache.subprocess.run = original_run


def main() -> None:
    assert BINARY.is_file() and os.access(BINARY, os.X_OK), BINARY
    original_binary = report_cache.DEFAULT_BINARY
    original_cache = os.environ.get("ELISA_PROOF_REPORT_CACHE")
    report_cache.DEFAULT_BINARY = BINARY
    try:
        with tempfile.TemporaryDirectory(prefix="elisa-missing-nested-report-cache-") as temporary:
            cache_dir = Path(temporary) / "reports"
            cache_dir.mkdir()
            (cache_dir / "pending").mkdir()

            fixture = Path(temporary) / "root.elisa"
            nested_dir = Path(temporary) / "nested"
            nested_dir.mkdir()
            outer = nested_dir / "outer.elisa"
            dependency = nested_dir / "limits.elisa"
            fixture.write_text(
                'include "nested/outer.elisa"\n'
                "def fetch() -> i64:\n"
                "    ensure result == Limit::VALUE\n"
                "    return Limit::VALUE\n",
                encoding="utf-8",
            )
            outer.write_text('include "limits.elisa"\n', encoding="utf-8")
            assert not dependency.exists()

            os.environ["ELISA_PROOF_REPORT_CACHE"] = str(cache_dir)
            prefetch.run_one(str(BINARY), str(cache_dir), str(fixture))
            missing_key = report_cache.cache_key(fixture, BINARY)
            missing_cached = cache_hit_without_runner(fixture)
            missing_report = json.loads(missing_cached[1])
            assert missing_cached[0] == 1 and missing_report["status"] == "failed"

            # The include walker must retain a missing nested path in the identity. When that
            # file appears, the existing failed report must no longer satisfy this fixture.
            dependency.write_text(
                "module Limit:\n    const VALUE: i64 = 1\n", encoding="utf-8"
            )
            appeared_key = report_cache.cache_key(fixture, BINARY)
            assert appeared_key != missing_key, "appearing nested include retained the old cache identity"

            fresh = report_cache.json_run(fixture, BINARY, timeout=120)
            fresh_report = json.loads(fresh[1])
            assert fresh[0] == 0 and fresh_report["status"] == "proved"
            assert fresh_report["goals"][-1]["goal"]["left"]["value"] == 1
            assert fresh != missing_cached, "appearing nested include returned the stale failed report"

            prefetch.run_one(str(BINARY), str(cache_dir), str(fixture))
            appeared_cached = cache_hit_without_runner(fixture)
            os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
            try:
                appeared_fresh = report_cache.json_run(fixture, BINARY, timeout=120)
            finally:
                os.environ["ELISA_PROOF_REPORT_CACHE"] = str(cache_dir)
            assert appeared_cached == fresh == appeared_fresh, (
                "nested dependency cached report differs from fresh verification"
            )
            print("new nested include: invalidated missing-path report; cached/fresh JSON equal")
    finally:
        report_cache.DEFAULT_BINARY = original_binary
        if original_cache is None:
            os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
        else:
            os.environ["ELISA_PROOF_REPORT_CACHE"] = original_cache


if __name__ == "__main__":
    main()
