#!/usr/bin/env python3
"""Focused contracts for the bounded P-01 baseline runner."""

import importlib.util
import hashlib
import json
import tempfile
from unittest import mock
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).with_name("p01_baseline.py")
SPEC = importlib.util.spec_from_file_location("p01_baseline", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

assert ("proof_kernel_core", MODULE.ROOT / "src/proof/kernel_core.elisa") in MODULE.FIXTURES
assert MODULE.EXPECTED_OUTCOMES["proof_kernel_core"] == {"status": "proved", "returncode": 0}
assert {name for name, _ in MODULE.FIXTURES} >= {
    "unsigned_boundary_refusal", "quantifier_success", "region_lending_success",
}
assert MODULE.EXPECTED_OUTCOMES["unsigned_boundary_refusal"] == {
    "status": "failed", "returncode": 1,
}
assert MODULE.EXPECTED_OUTCOMES["quantifier_success"] == {
    "status": "proved", "returncode": 0,
}
assert MODULE.EXPECTED_OUTCOMES["region_lending_success"] == {
    "status": "proved", "returncode": 0,
}
assert {name for name, _ in MODULE.FIXTURES} >= {"branch_join", "rejected_branch_join"}
sentinels = MODULE.load_sentinel_manifest()
assert all({"semantic_expectations", "expected_outcome", "sha256", "size_bytes", "path"}
           <= set(row) for row in sentinels.values())
manifest = json.loads(MODULE.SENTINEL_MANIFEST.read_text(encoding="utf-8"))
workloads = manifest["workloads"]
assert all(isinstance(row.get("workload"), str) and row["workload"] in workloads
           for row in sentinels.values())
assert {member for workload in workloads.values() for member in workload["members"]} == set(sentinels)
assert sentinels["adversarial"]["semantic_expectations"]["obligation_inventory_complete"] is False
assert (sentinels["adversarial"]["semantic_expectations"]["obligation_count"],
        len(sentinels["adversarial"]["semantic_expectations"]["obligation_ids"])) == (78, 77)
pair = json.loads(MODULE.SENTINEL_MANIFEST.read_text(encoding="utf-8"))["workloads"]["branch_join_pair"]
assert pair["members"] == ["branch_join", "rejected_branch_join"]
for name, count, status in (("branch_join", 12, "proved_with_replay_gaps"),
                            ("rejected_branch_join", 6, "failed")):
    fixture = sentinels[name]
    expected = fixture["semantic_expectations"]
    assert fixture["expected_outcome"]["status"] == status
    assert fixture["expected_outcome"]["returncode"] == (0 if status == "proved" else 1)
    assert MODULE.identity(MODULE.ROOT / fixture["path"]) == {
        "sha256": fixture["sha256"], "size_bytes": fixture["size_bytes"],
    }
    assert expected["obligation_count"] == count
    assert expected["obligation_ids"] == list(range(count))
    assert len(expected["obligation_details"]) == count
    assert sum(item["result"] == "proved" for item in expected["obligation_details"]) == expected["proven"]
    assert sum(item["result"] == "unproven" for item in expected["obligation_details"]) == expected["unproven"]
    assert expected["failed"] <= expected["unproven"]
    assert expected["trusted_assumptions"] == 0
    assert expected["replay_certificates"] == expected["replayed"] + expected["replay_gaps"]
    assert fixture["budget_classification"] == pair["budget_classification"]
    assert pair["budget_classification"] == {
        "classification": "standard-bounded", "timeout_seconds": 20,
        "rss_limit_kib": 1500000, "output_limit_bytes": MODULE.MAX_OUTPUT_BYTES,
    }

# The checked-in corpus is a measurement input, so stale or incomplete rows must fail before a
# sample can be collected. Exercise identity, expected semantics, assumptions, and replay fields.
with tempfile.TemporaryDirectory(prefix="p01-manifest-mutations-") as temporary:
    manifest_path = Path(temporary) / "sentinels.json"
    original_manifest = manifest
    mutations = []
    missing_fixture = json.loads(json.dumps(original_manifest))
    missing_fixture["fixtures"].pop("real_small")
    mutations.append((missing_fixture, "do not match"))
    missing_digest = json.loads(json.dumps(original_manifest))
    missing_digest["fixtures"]["real_small"].pop("sha256")
    mutations.append((missing_digest, "identity is incomplete"))
    stale_path = json.loads(json.dumps(original_manifest))
    stale_path["fixtures"]["real_small"]["sha256"] = "0" * 64
    mutations.append((stale_path, "identity changed"))
    missing_semantics = json.loads(json.dumps(original_manifest))
    missing_semantics["fixtures"]["real_small"].pop("semantic_expectations")
    mutations.append((missing_semantics, "semantic expectations are missing"))
    wrong_status = json.loads(json.dumps(original_manifest))
    wrong_status["fixtures"]["real_small"]["expected_outcome"]["status"] = "failed"
    mutations.append((wrong_status, "inconsistent"))
    omitted_goal = json.loads(json.dumps(original_manifest))
    omitted_goal["fixtures"]["real_small"]["semantic_expectations"]["obligation_details"].pop()
    mutations.append((omitted_goal, "obligation/assumption identity disagrees"))
    missing_assumptions = json.loads(json.dumps(original_manifest))
    missing_assumptions["fixtures"]["real_small"]["semantic_expectations"].pop(
        "trusted_assumption_details")
    mutations.append((missing_assumptions, "obligation/assumption inventory is incomplete"))
    replay_gap = json.loads(json.dumps(original_manifest))
    replay_gap["fixtures"]["real_small"]["semantic_expectations"]["replay_gaps"] = 1
    mutations.append((replay_gap, "semantic/replay totals are inconsistent"))
    malformed_row = json.loads(json.dumps(original_manifest))
    malformed_row["fixtures"]["real_small"]["semantic_expectations"]["obligation_details"][0]["result"] = "unknown"
    mutations.append((malformed_row, "obligation row is malformed"))
    missing_group = json.loads(json.dumps(original_manifest))
    missing_group["workloads"].pop("branch_join_pair")
    mutations.append((missing_group, "does not cover fixtures"))
    missing_member = json.loads(json.dumps(original_manifest))
    missing_member["workloads"]["branch_join_pair"]["members"] = ["branch_join"]
    mutations.append((missing_member, "does not cover fixtures"))
    unknown_member = json.loads(json.dumps(original_manifest))
    unknown_member["workloads"]["branch_join_pair"]["members"][1] = "renamed-fixture"
    mutations.append((unknown_member, "names missing fixture"))
    duplicate_member = json.loads(json.dumps(original_manifest))
    duplicate_member["workloads"]["branch_join_pair"]["members"] = ["branch_join", "branch_join"]
    mutations.append((duplicate_member, "members are missing or duplicated"))
    stale_workload_reference = json.loads(json.dumps(original_manifest))
    stale_workload_reference["fixtures"]["real_small"]["workload"] = "renamed-workload"
    mutations.append((stale_workload_reference, "disagrees with workload identity"))
    for mutated, message in mutations:
        manifest_path.write_text(json.dumps(mutated), encoding="utf-8")
        with mock.patch.object(MODULE, "SENTINEL_MANIFEST", manifest_path):
            try:
                parsed = MODULE.load_sentinel_manifest()
                if message == "identity changed":
                    MODULE.validate_workload_identities(parsed)
            except RuntimeError as error:
                assert message in str(error), (message, error)
            else:
                raise AssertionError(f"P-01 accepted manifest mutation: {message}")
    missing_probe = json.loads(json.dumps(original_manifest))
    missing_probe.pop("semantic_probe")
    manifest_path.write_text(json.dumps(missing_probe), encoding="utf-8")
    with mock.patch.object(MODULE, "SENTINEL_MANIFEST", manifest_path):
        try:
            MODULE.load_sentinel_manifest()
        except RuntimeError as error:
            assert "probe provenance" in str(error)
        else:
            raise AssertionError("P-01 accepted a manifest without semantic-probe provenance")
    fixture_path = Path(temporary) / "real-small.elisa"
    fixture_path.write_text("def f() -> bool: return true\n", encoding="utf-8")
    with mock.patch.object(MODULE, "ROOT", Path(temporary)), \
            mock.patch.object(MODULE, "FIXTURES", (("real_small", fixture_path),)):
        pinned = {"real_small": {"path": "real-small.elisa", "source_lines": 1,
                                 **MODULE.identity(fixture_path)}}
        MODULE.validate_workload_identities(pinned)
        pinned["real_small"]["source_lines"] = 2
        try:
            MODULE.validate_workload_identities(pinned)
        except RuntimeError as error:
            assert "identity changed" in str(error)
        else:
            raise AssertionError("P-01 accepted a stale line-count workload identity")
        pinned["real_small"]["source_lines"] = 1
        fixture_path.write_text("def f() -> bool: return false\n", encoding="utf-8")
        try:
            MODULE.validate_workload_identities(pinned)
        except RuntimeError as error:
            assert "identity changed" in str(error)
        else:
            raise AssertionError("P-01 accepted a fixture changed after its digest was pinned")
        empty_path = Path(temporary) / "empty.elisa"
        empty_path.write_bytes(b"")
        with mock.patch.object(MODULE, "FIXTURES", (("empty", empty_path),)):
            MODULE.validate_workload_identities({"empty": {"path": "empty.elisa", "source_lines": 0,
                                                               **MODULE.identity(empty_path)}})

positive = sentinels["real_small"]["semantic_expectations"]
profile_measurement = {"stop_reason": None, "report_complete": True, "wall_seconds": 0.02,
                       "cpu_seconds": 0.01,
                       "phase_timings_seconds": {"proof_cli_invocation_wall": 0.02,
                           "proof_cli_child_cpu": 0.01, "baseline_harness_json_decode": 0.001},
                       "replay_gaps": positive["replay_gaps"],
                       "replay_certificates": positive["replay_certificates"],
                       "replayed": positive["replayed"], "goal_cache_hits": 0,
                       "goal_cache_misses": 0, "control_flow_steps": 0,
                       "live_facts_peak": 0, "status": "proved", "returncode": 0,
                       "obligations": positive["obligation_count"],
                       "obligation_ids": positive["obligation_ids"],
                       "obligation_details": positive["obligation_details"],
                       "trusted_assumption_details": positive["trusted_assumption_details"],
                       "proven": positive["proven"], "unproven": positive["unproven"],
                       "failed": positive["failed"],
                       "trusted_assumptions": positive["trusted_assumptions"],
                       "trusted_boundary_facts": positive["trusted_boundary_facts"],
                       "proof_certificates": positive["proof_certificates"]}
MODULE.check_report(profile_measurement, sentinels["real_small"]["expected_outcome"], positive)
branch_gap = {**profile_measurement, "status": "proved_with_replay_gaps", "returncode": 1,
              "obligations": 12, "obligation_ids": list(range(12)),
              "obligation_details": sentinels["branch_join"]["semantic_expectations"]["obligation_details"],
              "replay_gaps": 3}
try:
    MODULE.check_report(branch_gap, sentinels["branch_join"]["expected_outcome"],
                        sentinels["branch_join"]["semantic_expectations"])
except RuntimeError as error:
    assert "replay gaps" in str(error)
else:
    raise AssertionError("P-01 admitted the freshly observed branch-join replay gaps")
incomplete_inventory = {**profile_measurement, "status": "failed", "returncode": 1,
                        "obligations": 78, "obligation_ids": list(range(77)),
                        "obligation_details": sentinels["adversarial"]["semantic_expectations"]["obligation_details"],
                        "replay_gaps": 0, "replay_certificates": 0, "replayed": 0}
try:
    MODULE.check_report(incomplete_inventory, sentinels["adversarial"]["expected_outcome"],
                        sentinels["adversarial"]["semantic_expectations"])
except RuntimeError as error:
    assert "obligation inventory is incomplete" in str(error)
else:
    raise AssertionError("P-01 admitted a summary with a missing source-obligation row")
for invalid_timings, message in (
    ({"proof_cli_invocation_wall": 0.02, "proof_cli_child_cpu": 0.01}, "schema"),
    ({"proof_cli_invocation_wall": 0.02, "proof_cli_child_cpu": 0.01,
      "baseline_harness_json_decode": float("nan")}, "invalid baseline_harness_json_decode"),
    ({"proof_cli_invocation_wall": 0.03, "proof_cli_child_cpu": 0.01,
      "baseline_harness_json_decode": 0.001}, "disagrees with proof CLI invocation"),
    ({"proof_cli_invocation_wall": 0.02, "proof_cli_child_cpu": 0.02,
      "baseline_harness_json_decode": 0.001}, "disagrees with proof CLI child CPU"),
):
    invalid_measurement = {**profile_measurement, "phase_timings_seconds": invalid_timings}
    try:
        MODULE.check_report(invalid_measurement, sentinels["real_small"]["expected_outcome"], positive)
    except RuntimeError as error:
        assert message in str(error), (message, error)
    else:
        raise AssertionError(f"invalid P-01 phase timing was accepted: {invalid_timings}")
profile_measurement["trusted_assumptions"] = 1
try:
    MODULE.check_report(profile_measurement, sentinels["real_small"]["expected_outcome"], positive)
except RuntimeError as error:
    assert "trusted_assumptions" in str(error)
else:
    raise AssertionError("semantic workload profile drift was accepted")


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
            with mock.patch.object(MODULE, "ROOT", root), \
                    mock.patch.object(MODULE, "load_sentinel_manifest", return_value={
                "test": {"path": "fixture.elisa", "sha256": MODULE.identity(fixture)["sha256"],
                         "size_bytes": fixture.stat().st_size, "source_lines": 2,
                         "expected_outcome": {"status": "proved", "returncode": 0}},
            }):
                result = MODULE.run(SimpleNamespace(binary=binary, timeout=5, rss_limit_kib=500000,
                                                    rounds=2, warmup_runs=1))
                checksum_path = Path(str(manifest_path) + ".sha256")
                original_checksum = checksum_path.read_bytes()
                original_invoke = MODULE.invoke
                changed = [False]

                def mutate_manifest_during_measurement(*args, **kwargs):
                    row = original_invoke(*args, **kwargs)
                    if not changed[0]:
                        updated_manifest = json.loads(manifest_path.read_bytes())
                        updated_manifest["build_identity"] = "changed-during-measurement"
                        updated_bytes = json.dumps(updated_manifest, sort_keys=True).encode("utf-8")
                        manifest_path.write_bytes(updated_bytes)
                        checksum_path.write_text(hashlib.sha256(updated_bytes).hexdigest() + "\n",
                                                 encoding="ascii")
                        changed[0] = True
                    return row

                try:
                    with mock.patch.object(MODULE, "invoke", side_effect=mutate_manifest_during_measurement):
                        MODULE.run(SimpleNamespace(binary=binary, timeout=5, rss_limit_kib=500000,
                                                   rounds=1, warmup_runs=0))
                except RuntimeError as error:
                    assert "proof build identity changed during measurement" in str(error), error
                else:
                    raise AssertionError("P-01 accepted a build-manifest change during measurement")
                finally:
                    manifest_path.write_bytes(manifest_bytes)
                    checksum_path.write_bytes(original_checksum)
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
            with mock.patch.object(MODULE.os, "killpg", side_effect=PermissionError("denied")):
                limited = MODULE.invoke(binary, fixture, timeout=5, rss_limit_kib=500000)
            assert limited["stop_reason"] == "output_limit", limited
            assert limited["returncode"] is not None
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
