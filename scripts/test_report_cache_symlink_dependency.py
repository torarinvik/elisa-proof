#!/usr/bin/env python3
"""Ensure retargeting a symlinked include invalidates a report-cache entry."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORT_CACHE_SPEC = importlib.util.spec_from_file_location(
    "report_cache_symlink_dependency", ROOT / "scripts/report_cache.py"
)
assert REPORT_CACHE_SPEC and REPORT_CACHE_SPEC.loader
report_cache = importlib.util.module_from_spec(REPORT_CACHE_SPEC)
REPORT_CACHE_SPEC.loader.exec_module(report_cache)
PREFETCH_SPEC = importlib.util.spec_from_file_location(
    "prefetch_reports_symlink_dependency", ROOT / "scripts/prefetch_reports.py"
)
assert PREFETCH_SPEC and PREFETCH_SPEC.loader
prefetch = importlib.util.module_from_spec(PREFETCH_SPEC)
PREFETCH_SPEC.loader.exec_module(prefetch)


def main() -> None:
    previous_default_binary = report_cache.DEFAULT_BINARY
    previous_cache = os.environ.get("ELISA_PROOF_REPORT_CACHE")
    try:
        with tempfile.TemporaryDirectory(prefix="elisa-report-cache-symlink-dependency-") as temporary:
            root = Path(temporary)
            fixture = root / "proof.elisa"
            linked_dependency = root / "decision.elisa"
            proved_dependency = root / "proved.elisa"
            failed_dependency = root / "failed.elisa"
            executable = root / "elisa-proof"
            cache_dir = root / "reports"
            cache_dir.mkdir()
            (cache_dir / "pending").mkdir()
            fixture.write_text('include "decision.elisa"\n', encoding="utf-8")
            proved_dependency.write_text("proved\n", encoding="utf-8")
            failed_dependency.write_text("failed\n", encoding="utf-8")
            linked_dependency.symlink_to(proved_dependency.name)
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, re, sys\n"
                "fixture = pathlib.Path(sys.argv[-1])\n"
                "include = re.search(r'include \\\"([^\\\"]+)\\\"', fixture.read_text()).group(1)\n"
                "proved = (fixture.parent / include).read_text().strip() == 'proved'\n"
                "print(json.dumps({'status': 'proved' if proved else 'failed'}))\n"
                "raise SystemExit(0 if proved else 1)\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            report_cache.DEFAULT_BINARY = executable
            os.environ["ELISA_PROOF_REPORT_CACHE"] = str(cache_dir)

            prefetch.run_one(str(executable), str(cache_dir), str(fixture))
            proved_key = report_cache.cache_key(fixture, executable)
            original = report_cache._read_cached_entry(str(cache_dir / proved_key))
            assert original is not None and original[0] == 0
            assert json.loads(original[1])["status"] == "proved"

            # Keep the fixture and include spelling fixed; only the symlink target changes.
            linked_dependency.unlink()
            linked_dependency.symlink_to(failed_dependency.name)
            failed_key = report_cache.cache_key(fixture, executable)
            assert failed_key != proved_key, "symlink retarget retained the old report identity"

            original_run = report_cache.subprocess.run
            invocations = []

            def count_verifier_invocations(*args, **kwargs):
                invocations.append(args[0])
                return original_run(*args, **kwargs)

            report_cache.subprocess.run = count_verifier_invocations
            try:
                fresh_miss = report_cache.json_run(fixture, executable)
            finally:
                report_cache.subprocess.run = original_run
            assert len(invocations) == 1, "retargeted dependency should launch one fresh verifier"
            assert fresh_miss[0] == 1 and json.loads(fresh_miss[1])["status"] == "failed"

            prefetch.run_one(str(executable), str(cache_dir), str(fixture))
            cached = report_cache.json_run(fixture, executable)
            assert cached == fresh_miss, "retargeted dependency cached report differs from fresh run"
            assert report_cache._read_cached_entry(str(cache_dir / proved_key)) == original, (
                "retargeting unexpectedly rewrote the prior dependency's cache entry"
            )

            os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
            try:
                uncached = report_cache.json_run(fixture, executable)
            finally:
                os.environ["ELISA_PROOF_REPORT_CACHE"] = str(cache_dir)
            assert cached == uncached, "retargeted dependency cached and uncached reports differ"
            print("symlink include retarget: key changed, verifier reran once, cached/uncached reports equal")
    finally:
        report_cache.DEFAULT_BINARY = previous_default_binary
        if previous_cache is None:
            os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
        else:
            os.environ["ELISA_PROOF_REPORT_CACHE"] = previous_cache


if __name__ == "__main__":
    main()
