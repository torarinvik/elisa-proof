#!/usr/bin/env python3
"""Focused contracts for the bounded P-01 baseline runner."""

import importlib.util
import hashlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).with_name("p01_baseline.py")
SPEC = importlib.util.spec_from_file_location("p01_baseline", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

assert ("proof_kernel_core", MODULE.ROOT / "src/proof/kernel_core.elisa") in MODULE.FIXTURES
assert MODULE.EXPECTED_OUTCOMES["proof_kernel_core"] == {"status": "proved", "returncode": 0}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="p01-test-") as temporary:
        root = Path(temporary)
        binary = root / "proof"
        report = {"status": "proved", "verification_state": "proved",
                  "summary": {"obligations": 1, "proven": 1, "unproven": 0,
                              "semantic_errors": 0},
                  "declaration_details": [{"verified": True}], "goals": [{}],
                  "measurements": {"format": "elisa-proof-measurements-v1",
                                   "goal_cache_hits": 1, "goal_cache_misses": 2,
                                   "control_flow_steps": 3, "live_facts_peak": 4,
                                   "certificate_facts": 5, "largest_certificate_facts": 4,
                                   "repeated_certificate_fact_roots": 2, "fact_traces": 6,
                                   "kernel_nodes": 7, "kernel_nodes_shared": 3,
                                   "kernel_children": 8, "report_bytes": 900,
                                   "heaviest_functions": [{"name": "work", "goal_attempts": 1,
                                                           "certificate_kernel_facts": 4}]},
                  "replay": {"certificates": 1, "replayed": 1, "gaps": 0}}
        binary.write_text("#!/usr/bin/env python3\nimport json,sys\nprint(" +
                          repr(json.dumps(report)) + ")\nsys.stdout.write(' ' * 100000)\n", encoding="utf-8")
        binary.chmod(0o755)
        manifest_path = Path(str(binary) + ".manifest.json")
        manifest = {"build_identity": "test-id", "binary": {"sha256": MODULE.identity(binary)["sha256"]},
                    "proof": {"source_tree_sha256": "proof-tree"},
                    "frontend": {"revision": "frontend-rev", "tree": "frontend-tree"},
                    "compiler": {"product": {"sha256": "compiler-product"}},
                    "runtime": {"sha256": "runtime-object"}, "target": "test-target",
                    "optimization": "O2", "compile_mode": "strict"}
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
        manifest_path.write_bytes(manifest_bytes)
        Path(str(manifest_path) + ".sha256").write_text(
            hashlib.sha256(manifest_bytes).hexdigest() + "\n", encoding="ascii")
        fixture = root / "fixture.elisa"
        fixture.write_text("def proof():\n    ensure true\n", encoding="utf-8")
        old = MODULE.FIXTURES
        MODULE.FIXTURES = (("test", fixture),)
        try:
            result = MODULE.run(SimpleNamespace(binary=binary, timeout=5, rss_limit_kib=500000,
                                                rounds=2, warmup_runs=1))
        finally:
            MODULE.FIXTURES = old
        assert result["schema"] == "elisa-proof-p01-baseline-v3"
        assert result["binary"]["sha256"] == MODULE.identity(binary)["sha256"]
        assert result["build"]["available"] is True
        assert result["build"]["target"] == "test-target"
        assert result["build"]["runtime"]["sha256"] == "runtime-object"
        assert result["frontend"] == result["build"]["frontend"]
        assert result["runtime"] == result["build"]["runtime"]
        incomplete_manifest = dict(manifest)
        incomplete_manifest.pop("frontend")
        incomplete_bytes = json.dumps(incomplete_manifest, sort_keys=True).encode("utf-8")
        manifest_path.write_bytes(incomplete_bytes)
        Path(str(manifest_path) + ".sha256").write_text(
            hashlib.sha256(incomplete_bytes).hexdigest() + "\n", encoding="ascii")
        try:
            MODULE.build_identity(binary)
        except RuntimeError as error:
            assert "frontend revision/tree identity" in str(error)
        else:
            raise AssertionError("baseline accepted a manifest without a frontend identity")
        manifest_path.write_bytes(manifest_bytes)
        Path(str(manifest_path) + ".sha256").write_text(
            hashlib.sha256(manifest_bytes).hexdigest() + "\n", encoding="ascii")
        Path(str(manifest_path) + ".sha256").write_text("stale\n", encoding="ascii")
        try:
            MODULE.build_identity(binary)
        except RuntimeError as error:
            assert "checksum" in str(error)
        else:
            raise AssertionError("stale build-manifest checksum was accepted")
        Path(str(manifest_path) + ".sha256").unlink()
        try:
            MODULE.run(SimpleNamespace(binary=binary, timeout=5, rss_limit_kib=500000,
                                       rounds=1, warmup_runs=0))
        except RuntimeError as error:
            assert "requires a verified build manifest" in str(error)
        else:
            raise AssertionError("baseline accepted a binary without a verified build manifest")
        case = result["cases"][0]
        assert result["rounds"] == 2 and result["warmup_runs_per_fixture"] == 1
        assert set(case["scenarios"]) == {"cold", "warm", "no_op"}
        assert all(len(scenario["measurements"]) == 2
                   for scenario in case["scenarios"].values())
        assert case["source"]["sha256"] != case["comment_edit_source"]["sha256"]
        measurements = [item for scenario in case["scenarios"].values()
                        for item in scenario["measurements"]]
        assert all(item["replay_gaps"] == 0 for item in measurements)
        assert all(item["stdout_bytes"] > 65536 for item in measurements)
        assert all(isinstance(item["cpu_seconds"], (int, float)) for item in measurements)
        assert all(item["phase_timings_seconds"]["proof_cli_invocation_wall"] == item["wall_seconds"]
                   for item in measurements)
        assert all(isinstance(item["phase_timings_seconds"]["baseline_harness_json_decode"], (int, float))
                   for item in measurements)
        assert all(item["phase_timings_seconds"]["proof_cli_child_cpu"] == item["cpu_seconds"]
                   for item in measurements)
        assert result["phase_timing_availability"]["resolution_and_semantics"] == \
            "unavailable-single-opaque-semantic-api-call"
        assert result["phase_timing_availability"]["proof_json_reporting"].startswith("unavailable-")
        assert all(item["peak_rss_kib"] > 0 for item in measurements), measurements
        assert case["scenarios"]["cold"]["median_cpu_seconds"] is not None
        MODULE.check_report(measurements[0], MODULE.EXPECTED_OUTCOMES["real_small"])
        assert measurements[0]["goal_cache_hits"] == 1
        assert measurements[0]["goal_cache_misses"] == 2
        assert measurements[0]["control_flow_steps"] == 3
        assert measurements[0]["live_facts_peak"] == 4
        assert measurements[0]["proof_report_measurements"] == report["measurements"]
        assert measurements[0]["proof_report_measurements"]["kernel_nodes_shared"] == 3
        assert measurements[0]["proof_report_measurements"]["report_bytes"] == 900
        assert measurements[0]["proof_report_measurements"]["heaviest_functions"][0]["name"] == "work"
        old_output_limit = MODULE.MAX_OUTPUT_BYTES
        try:
            MODULE.MAX_OUTPUT_BYTES = 1024
            limited = MODULE.invoke(binary, fixture, timeout=5, rss_limit_kib=500000)
            assert limited["stop_reason"] == "output_limit", limited
            assert limited["stdout_bytes"] > limited["stdout_sha256_bytes"]
            assert limited["stdout_sha256_complete"] is False
        finally:
            MODULE.MAX_OUTPUT_BYTES = old_output_limit
        negative_expected = MODULE.EXPECTED_OUTCOMES["adversarial"]
        try:
            MODULE.check_report(measurements[0], negative_expected)
        except RuntimeError as error:
            assert "negative fixture was accepted" in str(error)
        else:
            raise AssertionError("negative fixture acceptance was not detected")
        malformed = {"report_complete": False, "stop_reason": None}
        try:
            MODULE.check_report(malformed)
        except RuntimeError as error:
            assert "complete JSON" in str(error)
        else:
            raise AssertionError("incomplete report was accepted")
        print("P-01 baseline: fixed identities, scenario labels and replay completeness enforced")


if __name__ == "__main__":
    main()
