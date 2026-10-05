#!/usr/bin/env python3
"""Editing a transitive include must invalidate the cached verifier report."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CACHE_SPEC = importlib.util.spec_from_file_location(
    "report_cache_nested_edit", ROOT / "scripts/report_cache.py"
)
assert CACHE_SPEC and CACHE_SPEC.loader
report_cache = importlib.util.module_from_spec(CACHE_SPEC)
CACHE_SPEC.loader.exec_module(report_cache)
PREFETCH_SPEC = importlib.util.spec_from_file_location(
    "prefetch_reports_nested_edit", ROOT / "scripts/prefetch_reports.py"
)
assert PREFETCH_SPEC and PREFETCH_SPEC.loader
prefetch = importlib.util.module_from_spec(PREFETCH_SPEC)
PREFETCH_SPEC.loader.exec_module(prefetch)


def main() -> None:
    previous_default_binary = report_cache.DEFAULT_BINARY
    previous_cache = os.environ.get("ELISA_PROOF_REPORT_CACHE")
    try:
        with tempfile.TemporaryDirectory(prefix="elisa-report-cache-nested-edit-") as temporary:
            root = Path(temporary)
            fixture = root / "proof.elisa"
            outer = root / "nested" / "outer.elisa"
            dependency = root / "nested" / "deep" / "decision.elisa"
            executable = root / "elisa-proof"
            cache_dir = root / "reports"
            cache_dir.mkdir()
            (cache_dir / "pending").mkdir()
            outer.parent.mkdir()
            dependency.parent.mkdir()
            fixture.write_text('include "nested/outer.elisa"\n', encoding="utf-8")
            outer.write_text('include "deep/decision.elisa"\n', encoding="utf-8")
            dependency.write_text("proved\n", encoding="utf-8")
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, sys\n"
                "source = pathlib.Path(sys.argv[-1])\n"
                "decision = (source.parent / 'nested/deep/decision.elisa').read_text().strip()\n"
                "status = 'proved' if decision == 'proved' else 'failed'\n"
                "print(json.dumps({'status': status, 'decision': decision}))\n"
                "raise SystemExit(0 if status == 'proved' else 1)\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            report_cache.DEFAULT_BINARY = executable
            os.environ["ELISA_PROOF_REPORT_CACHE"] = str(cache_dir)

            prefetch.run_one(str(executable), str(cache_dir), str(fixture))
            proved_key = report_cache.cache_key(fixture, executable)
            original = report_cache._read_cached_entry(str(cache_dir / proved_key))
            assert original is not None and original[0] == 0
            assert json.loads(original[1]) == {"status": "proved", "decision": "proved"}

            # Keep both include directives fixed; only the transitive leaf changes.
            dependency.write_text("failed\n", encoding="utf-8")
            failed_key = report_cache.cache_key(fixture, executable)
            assert failed_key != proved_key, "transitive include edit retained the old cache identity"

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
            assert len(invocations) == 1, "transitive include edit should launch one fresh verifier"
            assert fresh_miss[0] == 1
            assert json.loads(fresh_miss[1]) == {"status": "failed", "decision": "failed"}

            prefetch.run_one(str(executable), str(cache_dir), str(fixture))
            cached = report_cache.json_run(fixture, executable)
            assert cached == fresh_miss, "edited nested dependency cached report differs from fresh run"
            assert report_cache._read_cached_entry(str(cache_dir / proved_key)) == original, (
                "editing a nested dependency unexpectedly rewrote the prior cache entry"
            )

            os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
            try:
                uncached = report_cache.json_run(fixture, executable)
            finally:
                os.environ["ELISA_PROOF_REPORT_CACHE"] = str(cache_dir)
            assert cached == uncached, "edited nested dependency cached and uncached reports differ"
            print("nested include edit: key changed, verifier reran once, cached/uncached reports equal")
    finally:
        report_cache.DEFAULT_BINARY = previous_default_binary
        if previous_cache is None:
            os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
        else:
            os.environ["ELISA_PROOF_REPORT_CACHE"] = previous_cache


if __name__ == "__main__":
    main()
