#!/usr/bin/env python3
"""Compare prefetched and fresh proof reports on real fixtures and the built CLI."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORT_CACHE_SPEC = importlib.util.spec_from_file_location(
    "report_cache_real", ROOT / "scripts/report_cache.py"
)
assert REPORT_CACHE_SPEC and REPORT_CACHE_SPEC.loader
report_cache = importlib.util.module_from_spec(REPORT_CACHE_SPEC)
REPORT_CACHE_SPEC.loader.exec_module(report_cache)
PREFETCH_SPEC = importlib.util.spec_from_file_location(
    "prefetch_reports_real", ROOT / "scripts/prefetch_reports.py"
)
assert PREFETCH_SPEC and PREFETCH_SPEC.loader
prefetch = importlib.util.module_from_spec(PREFETCH_SPEC)
PREFETCH_SPEC.loader.exec_module(prefetch)

BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof")).resolve()
FIXTURES = (
    (ROOT / "examples/perf_luna_accept.elisa", "proved", 0),
    (ROOT / "examples/perf_luna_refusal.elisa", "failed", 1),
)


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
        with tempfile.TemporaryDirectory(prefix="elisa-real-report-cache-") as temporary:
            os.environ["ELISA_PROOF_REPORT_CACHE"] = temporary
            (Path(temporary) / "pending").mkdir()
            for fixture, expected_status, expected_rc in FIXTURES:
                prefetch.run_one(str(BINARY), temporary, str(fixture))
                key = report_cache.cache_key(fixture, BINARY)
                entry = report_cache._read_cached_entry(str(Path(temporary) / key))
                assert entry is not None, (fixture, "prefetch did not publish a valid cache entry")
                cached_rc, cached_payload = cache_hit_without_runner(fixture)
                assert (cached_rc, cached_payload) == entry, (fixture, "cache lookup missed")

                os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
                try:
                    fresh_rc, fresh_payload = report_cache.json_run(fixture, BINARY, timeout=120)
                finally:
                    os.environ["ELISA_PROOF_REPORT_CACHE"] = temporary
                assert (cached_rc, cached_payload) == (fresh_rc, fresh_payload), (
                    fixture, "cached and fresh report bytes differ"
                )
                report = json.loads(cached_payload)
                assert cached_rc == expected_rc, (fixture, cached_rc)
                assert report.get("status") == expected_status, (fixture, report.get("status"))
                replay = report.get("replay", {})
                assert replay.get("gaps") == 0, (fixture, replay)
                assert replay.get("certificates") == replay.get("replayed"), (fixture, replay)
                print(
                    f"{fixture.relative_to(ROOT)}: {report['summary']['proven']}/"
                    f"{report['summary']['obligations']} proven; "
                    f"{replay['replayed']}/{replay['certificates']} replayed"
                )

            # A real included module changes the semantic theorem while the root file path and
            # bytes stay fixed. The dependency digest must select a fresh verifier report.
            dependency = Path(temporary) / "limits.elisa"
            source = Path(temporary) / "included_dependency.elisa"
            source.write_text(
                'include "limits.elisa"\n'
                "def fetch() -> i64:\n"
                "    ensure result == Limit::VALUE\n"
                "    return Limit::VALUE\n",
                encoding="utf-8",
            )
            dependency.write_text("module Limit:\n    const VALUE: i64 = 0\n", encoding="utf-8")
            prefetch.run_one(str(BINARY), temporary, str(source))
            original_key = report_cache.cache_key(source, BINARY)
            original_cached = cache_hit_without_runner(source)
            original_report = json.loads(original_cached[1])
            assert original_cached[0] == 0 and original_report["status"] == "proved"
            assert original_report["goals"][-1]["goal"]["left"]["value"] == 0

            dependency.write_text("module Limit:\n    const VALUE: i64 = 1\n", encoding="utf-8")
            changed_key = report_cache.cache_key(source, BINARY)
            assert changed_key != original_key, "included real source edit kept the old cache identity"
            changed = report_cache.json_run(source, BINARY, timeout=120)
            changed_report = json.loads(changed[1])
            assert changed[0] == 0 and changed_report["status"] == "proved"
            assert changed_report["goals"][-1]["goal"]["left"]["value"] == 1
            assert changed != original_cached, "included source edit returned a stale theorem report"

            prefetch.run_one(str(BINARY), temporary, str(source))
            changed_cached = cache_hit_without_runner(source)
            os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
            try:
                changed_fresh = report_cache.json_run(source, BINARY, timeout=120)
            finally:
                os.environ["ELISA_PROOF_REPORT_CACHE"] = temporary
            assert changed_cached == changed == changed_fresh, (
                "changed included source cached report differs from fresh verification"
            )
            assert changed_report["replay"]["gaps"] == 0
            assert changed_report["replay"]["certificates"] == changed_report["replay"]["replayed"]
            print("included module edit: fresh theorem identity, complete replay, cached/fresh JSON equal")
    finally:
        report_cache.DEFAULT_BINARY = original_binary
        if original_cache is None:
            os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
        else:
            os.environ["ELISA_PROOF_REPORT_CACHE"] = original_cache
    print("real report cache: prefetched and fresh proof reports matched byte-for-byte")


if __name__ == "__main__":
    main()
