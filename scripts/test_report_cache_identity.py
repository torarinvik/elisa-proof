#!/usr/bin/env python3
"""Focused regression controls for report-cache identity and entry validation."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("report_cache", ROOT / "scripts/report_cache.py")
cache = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cache)
PREFETCH_SPEC = importlib.util.spec_from_file_location("prefetch_reports", ROOT / "scripts/prefetch_reports.py")
prefetch = importlib.util.module_from_spec(PREFETCH_SPEC)
PREFETCH_SPEC.loader.exec_module(prefetch)


def main():
    with tempfile.TemporaryDirectory(prefix="elisa-report-cache-identity-") as temporary:
        root = Path(temporary)
        fixture = root / "float_mode.elisa"
        dependency = root / "decision.elisa"
        binary = root / "elisa-proof"
        fixture.write_text('include "decision.elisa"\n', encoding="utf-8")
        # proof_float_mode gates tactic/decision behavior; editing this included source must
        # invalidate a report even when the top-level fixture path stays constant.
        dependency.write_text("const marker: f64 = 1.0\n", encoding="utf-8")
        binary.write_bytes(b"proof-binary-v1")
        key = cache.cache_key(fixture, binary)
        dependency.write_text("const marker: i64 = 1\n", encoding="utf-8")
        assert cache.cache_key(fixture, binary) != key, "included semantic input did not invalidate"

        key = cache.cache_key(fixture, binary)
        binary.write_bytes(b"proof-binary-v2")
        assert cache.cache_key(fixture, binary) != key, "binary change did not invalidate"

        key = cache.cache_key(fixture, binary)
        original_machine = cache.platform.machine
        try:
            cache.platform.machine = lambda: "other-test-target"
            assert cache.cache_key(fixture, binary) != key, "runtime target change did not invalidate"
        finally:
            cache.platform.machine = original_machine

        key = cache.cache_key(fixture, binary)
        previous = os.environ.get("ELISA_PROOF_FLOAT_MODE")
        try:
            os.environ["ELISA_PROOF_FLOAT_MODE"] = "strict"
            changed_mode = cache.cache_key(fixture, binary)
            assert changed_mode != key, "proof-affecting environment did not invalidate"
        finally:
            if previous is None:
                os.environ.pop("ELISA_PROOF_FLOAT_MODE", None)
            else:
                os.environ["ELISA_PROOF_FLOAT_MODE"] = previous

        # Worker scheduling settings do not change a report and are intentionally omitted so
        # prefetch and serial readers derive the same identity.
        key = cache.cache_key(fixture, binary)
        os.environ["ELISA_PROOF_REPORT_CACHE"] = str(root / "worker-cache")
        try:
            assert cache.cache_key(fixture, binary) == key
        finally:
            os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)

        original_default = cache.DEFAULT_BINARY
        cache.DEFAULT_BINARY = binary
        original_recipes = cache.REPORT_CACHE_RECIPES
        assert {path.name for path in original_recipes} == {"report_cache.py", "prefetch_reports.py"}, "report cache key omits an implementation recipe"
        cache_recipe = root / "report-cache-recipe.py"
        cache_recipe.write_text("cache recipe v1", encoding="utf-8")
        cache.REPORT_CACHE_RECIPES = (cache_recipe,)
        previous_cache = os.environ.get("ELISA_PROOF_REPORT_CACHE")
        report_cache = root / "reports"
        report_cache.mkdir()
        (report_cache / "pending").mkdir()
        os.environ["ELISA_PROOF_REPORT_CACHE"] = str(report_cache)
        try:
            cache_key = cache.cache_key(fixture, binary)
            valid_payload = json.dumps({"status": "proved"})
            (report_cache / (cache_key + ".json")).write_text(valid_payload, encoding="utf-8")
            (report_cache / (cache_key + ".sha256")).write_text(
                hashlib.sha256(valid_payload.encode("utf-8")).hexdigest() + "\n", encoding="ascii")
            (report_cache / (cache_key + ".rc")).write_text("0\n", encoding="ascii")
            assert cache._cached(binary, fixture) == (0, valid_payload), "valid digest entry missed"

            cache_recipe.write_text("cache recipe v2", encoding="utf-8")
            assert cache._cached(binary, fixture) is None, "changed cache recipe reused an old report"
            cache_recipe.write_text("cache recipe v1", encoding="utf-8")

            # Keep the old digest and update both valid JSON and its matching status: only
            # payload-integrity validation can detect this mutation.
            (report_cache / (cache_key + ".json")).write_text(
                json.dumps({"status": "failed"}), encoding="utf-8")
            (report_cache / (cache_key + ".rc")).write_text("1\n", encoding="ascii")
            assert cache._cached(binary, fixture) is None, "valid-JSON payload mutation was accepted"

            (report_cache / (cache_key + ".json")).write_text("{bad json", encoding="utf-8")
            assert cache._cached(binary, fixture) is None, "corrupt entry was accepted"

            key = cache.cache_key(fixture, binary)
            (report_cache / "pending" / key).touch()
            old_wait = cache.PENDING_WAIT_SECONDS
            cache.PENDING_WAIT_SECONDS = 0.02
            try:
                assert cache._cached(binary, fixture) is None, "incomplete pending entry was accepted"
            finally:
                cache.PENDING_WAIT_SECONDS = old_wait
                (report_cache / "pending" / key).unlink(missing_ok=True)

            cache.REPORT_CACHE_RECIPES = original_recipes
            writer_binary = root / "proof-writer"
            writer_binary.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, sys\n"
                "fixture = pathlib.Path(sys.argv[-1])\n"
                "dependency = fixture.parent / 'decision.elisa'\n"
                "is_float = 'f64' in dependency.read_text(encoding='utf-8')\n"
                "status = 'proved' if is_float else 'failed'\n"
                "print(json.dumps({'status': status, 'mode': 'float' if is_float else 'integer'}))\n"
                "raise SystemExit(0 if is_float else 1)\n", encoding="utf-8")
            writer_binary.chmod(0o755)
            cache.DEFAULT_BINARY = writer_binary
            dependency.write_text("const marker: f64 = 1.0\n", encoding="utf-8")
            prefetch.run_one(str(writer_binary), str(report_cache), str(fixture))
            writer_key = cache.cache_key(fixture, writer_binary)
            writer_payload = (report_cache / (writer_key + ".json")).read_bytes()
            assert (report_cache / (writer_key + ".sha256")).read_text(encoding="ascii").strip() == hashlib.sha256(writer_payload).hexdigest(), "prefetch writer omitted or miscomputed digest"
            cached_float = cache.json_run(fixture, writer_binary)
            assert cached_float == (0, writer_payload.decode("utf-8")), "prefetched float-mode result failed validation"
            active_cache = os.environ.pop("ELISA_PROOF_REPORT_CACHE")
            try:
                uncached_float = cache.json_run(fixture, writer_binary)
            finally:
                os.environ["ELISA_PROOF_REPORT_CACHE"] = active_cache
            assert cached_float == uncached_float, "float-mode cached and uncached reports differed"

            # The included type switches proof_float_mode; its digest must produce a new report
            # identity and the prefetched result must match a fresh verifier invocation.
            dependency.write_text("const marker: i64 = 1\n", encoding="utf-8")
            integer_miss = cache.json_run(fixture, writer_binary)
            assert integer_miss[0] == 1 and json.loads(integer_miss[1])["mode"] == "integer", "mode switch reused the float report"
            prefetch.run_one(str(writer_binary), str(report_cache), str(fixture))
            cached_integer = cache.json_run(fixture, writer_binary)
            active_cache = os.environ.pop("ELISA_PROOF_REPORT_CACHE")
            try:
                uncached_integer = cache.json_run(fixture, writer_binary)
            finally:
                os.environ["ELISA_PROOF_REPORT_CACHE"] = active_cache
            assert cached_integer == uncached_integer == integer_miss, "integer-mode cached and uncached reports differed"
        finally:
            cache.DEFAULT_BINARY = original_default
            cache.REPORT_CACHE_RECIPES = original_recipes
            if previous_cache is None:
                os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
            else:
                os.environ["ELISA_PROOF_REPORT_CACHE"] = previous_cache
    print("report cache identity: include, binary, mode and corrupt-entry controls passed")


if __name__ == "__main__":
    main()
