#!/usr/bin/env python3
"""Focused regression controls for report-cache identity and entry validation."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("report_cache", ROOT / "scripts/report_cache.py")
cache = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cache)


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
        previous_cache = os.environ.get("ELISA_PROOF_REPORT_CACHE")
        report_cache = root / "reports"
        report_cache.mkdir()
        os.environ["ELISA_PROOF_REPORT_CACHE"] = str(report_cache)
        try:
            cache_key = cache.cache_key(fixture, binary)
            (report_cache / (cache_key + ".json")).write_text("{bad json", encoding="utf-8")
            (report_cache / (cache_key + ".rc")).write_text("0\n", encoding="utf-8")
            assert cache._cached(binary, fixture) is None, "corrupt entry was accepted"
            (report_cache / (cache_key + ".json")).write_text(
                json.dumps({"status": "failed"}), encoding="utf-8")
            assert cache._cached(binary, fixture) is None, "exit/verdict mismatch was accepted"
        finally:
            cache.DEFAULT_BINARY = original_default
            if previous_cache is None:
                os.environ.pop("ELISA_PROOF_REPORT_CACHE", None)
            else:
                os.environ["ELISA_PROOF_REPORT_CACHE"] = previous_cache
    print("report cache identity: include, binary, mode and corrupt-entry controls passed")


if __name__ == "__main__":
    main()
