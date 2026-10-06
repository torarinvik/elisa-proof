#!/usr/bin/env python3
"""Pinned P-01 workload identities and proof/compiler artifact validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENTINEL_SCHEMA = "elisa-proof-p01-sentinels-v4"
SHAPE_METRICS = {
    "source_imported_bytes": "source.bytes",
    "source_file_count": "len(files)",
    "token_count": None,
    "ast_node_count": None,
    "declaration_count": "measurements.declarations",
    "fact_trace_count": "measurements.fact_traces",
    "certificate_fact_count": "measurements.certificate_facts",
    "branch_count": None,
    "call_count": None,
    "loop_count": None,
    "certificate_count": "replay.certificates",
    "kernel_node_count": "measurements.kernel_nodes",
    "kernel_child_count": "measurements.kernel_children",
    "package_node_count": None,
}
SENTINEL_MANIFEST = ROOT / "scripts" / "p01_sentinels.json"
MAX_OUTPUT_BYTES = 128 * 1024 * 1024
FIXTURES = (
    ("real_small", ROOT / "examples/perf_luna_accept.elisa"),
    ("real_refusal", ROOT / "examples/perf_luna_refusal.elisa"),
    # Dogfood the proof kernel itself as a pinned real-code baseline fixture.
    ("proof_kernel_core", ROOT / "src/proof/kernel_core.elisa"),
    ("adversarial", ROOT / "examples/rejected_symbolic_quantifier.elisa"),
    ("qualified_constants", ROOT / "examples/qualified_constants_statements.elisa"),
    ("qualified_constant_refusal", ROOT / "examples/rejected_qualified_constants_statements.elisa"),
    ("unsigned_boundary_refusal", ROOT / "examples/counterexample_unsigned_boundaries.elisa"),
    ("quantifier_success", ROOT / "examples/quantifier.elisa"),
    ("region_lending_success", ROOT / "examples/region_lend_calls.elisa"),
    ("branch_join", ROOT / "examples/branch_join.elisa"),
    ("rejected_branch_join", ROOT / "examples/rejected_branch_join.elisa"),
    ("call_chain_success", ROOT / "examples/deterministic_call_chain.elisa"),
    ("call_chain_refusal", ROOT / "examples/rejected_deterministic_call_chain.elisa"),
    ("match_success", ROOT / "examples/value_match.elisa"),
    ("match_refusal", ROOT / "examples/rejected_value_match.elisa"),
    ("loop_invariant", ROOT / "examples/loop_counter_invariant.elisa"),
    ("malformed_loop_source", ROOT / "examples/malformed_or_chain_loop_update.elisa"),
    ("import_graph", ROOT / "examples/import_empty_root.elisa"),
    ("fact_growth", ROOT / "examples/fact_growth_work_budget.elisa"),
)
def load_sentinel_manifest() -> dict:
    try:
        payload = json.loads(SENTINEL_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read P-01 sentinel manifest: {error}") from error
    if payload.get("schema") != SENTINEL_SCHEMA or not isinstance(payload.get("fixtures"), dict):
        raise RuntimeError("P-01 sentinel manifest has an unsupported schema")
    if payload.get("shape_metrics") != SHAPE_METRICS:
        raise RuntimeError("P-01 semantic-shape metric inventory is missing, changed, or malformed")
    fixtures = payload["fixtures"]
    probe = payload.get("semantic_probe")
    probe_keys = ("proof_head", "proof_source_tree_sha256", "compiler_source_revision",
                  "compiler_product_sha256", "frontend_tree", "runtime_sha256",
                  "proof_binary_sha256", "replay_binary_sha256", "target", "optimization",
                  "compile_mode", "generation")
    if not isinstance(probe, dict) or any(not isinstance(probe.get(key), str) or not probe[key]
                                          for key in probe_keys):
        raise RuntimeError("P-01 semantic probe provenance is missing or incomplete")
    probe_hashes = ("proof_source_tree_sha256", "compiler_product_sha256",
                    "runtime_sha256", "proof_binary_sha256", "replay_binary_sha256")
    if any(len(probe[key]) != 64 or any(char not in "0123456789abcdef" for char in probe[key])
           for key in probe_hashes):
        raise RuntimeError("P-01 semantic probe provenance contains a malformed digest")
    for key in ("proof_head", "compiler_source_revision", "frontend_tree"):
        if len(probe[key]) != 40 or any(char not in "0123456789abcdef" for char in probe[key]):
            raise RuntimeError("P-01 semantic probe provenance contains a malformed revision")
    expected_names = {name for name, _ in FIXTURES}
    if set(fixtures) != expected_names:
        raise RuntimeError("P-01 fixtures do not match the versioned sentinel manifest")
    semantic_counts = ("obligation_count", "proven", "unproven", "failed",
                       "obligation_detail_proven", "obligation_detail_unproven",
                       "trusted_assumptions", "trusted_boundary_facts", "proof_certificates",
                       "replay_certificates", "replayed", "replay_gaps")
    for name, row in fixtures.items():
        if not isinstance(row, dict):
            raise RuntimeError(f"P-01 workload identity is malformed for {name}")
        digest = row.get("sha256")
        size = row.get("size_bytes")
        line_count = row.get("source_lines")
        if (not isinstance(row.get("path"), str) or not row["path"]
                or not isinstance(digest, str) or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
                or isinstance(size, bool) or not isinstance(size, int) or size < 0
                or isinstance(line_count, bool) or not isinstance(line_count, int) or line_count < 0):
            raise RuntimeError(f"P-01 workload identity is incomplete for {name}")
        outcome = row.get("expected_outcome")
        if (not isinstance(outcome, dict)
                or outcome.get("status") not in {"proved", "failed", "proved_with_replay_gaps"}
                or isinstance(outcome.get("returncode"), bool)
                or not isinstance(outcome.get("returncode"), int)
                or outcome.get("returncode") != (0 if outcome["status"] == "proved" else 1)):
            raise RuntimeError(f"P-01 expected status is incomplete or inconsistent for {name}")
        if row.get("identity_only") is True:
            continue
        semantic = row.get("semantic_expectations")
        if not isinstance(semantic, dict):
            raise RuntimeError(f"P-01 semantic expectations are missing for {name}")
        if any(isinstance(semantic.get(key), bool) or not isinstance(semantic.get(key), int)
               or semantic[key] < 0 for key in semantic_counts):
            raise RuntimeError(f"P-01 semantic counts are incomplete for {name}")
        ids = semantic.get("obligation_ids")
        details = semantic.get("obligation_details")
        assumption_details = semantic.get("trusted_assumption_details")
        inventory_complete = semantic.get("obligation_inventory_complete")
        if (not isinstance(ids, list) or any(isinstance(item, bool) or not isinstance(item, int)
                                             for item in ids)
                or len(set(ids)) != len(ids)
                or not isinstance(details, list)
                or not isinstance(assumption_details, list)
                or not isinstance(inventory_complete, bool)):
            raise RuntimeError(f"P-01 obligation/assumption inventory is incomplete for {name}")
        if (len(details) != len(ids)
                or (inventory_complete and len(ids) != semantic["obligation_count"])
                or [item.get("id") if isinstance(item, dict) else None for item in details] != ids
                or any(isinstance(item, bool) or not isinstance(item, int)
                       for item in (detail.get("id") for detail in details if isinstance(detail, dict)))
                or semantic["trusted_assumptions"] != len(assumption_details)):
            raise RuntimeError(f"P-01 obligation/assumption identity disagrees for {name}")
        if any(not isinstance(item, dict)
               or isinstance(item.get("id"), bool) or not isinstance(item.get("id"), int)
               or not isinstance(item.get("function"), str)
               or isinstance(item.get("line"), bool) or not isinstance(item.get("line"), int)
               or not isinstance(item.get("rule"), str)
               or item.get("result") not in ("proved", "unproven")
               for item in details):
            raise RuntimeError(f"P-01 obligation row is malformed for {name}")
        if (semantic["proven"] + semantic["unproven"] != semantic["obligation_count"]
                or semantic["failed"] > semantic["unproven"]
                or semantic["obligation_detail_proven"] + semantic["obligation_detail_unproven"] != len(details)
                or (inventory_complete and (semantic["obligation_detail_proven"] != semantic["proven"]
                                            or semantic["obligation_detail_unproven"] != semantic["unproven"]))
                or semantic["proof_certificates"] != semantic["replay_certificates"]
                or semantic["replay_certificates"] != semantic["replayed"] + semantic["replay_gaps"]):
            raise RuntimeError(f"P-01 semantic/replay totals are inconsistent for {name}")
        if (sum(item.get("result") == "proved" for item in details if isinstance(item, dict))
                != semantic["obligation_detail_proven"]
                or sum(item.get("result") == "unproven" for item in details if isinstance(item, dict))
                != semantic["obligation_detail_unproven"]
                or any(not isinstance(item, dict) or item.get("result") not in {"proved", "unproven"}
                       for item in details)):
            raise RuntimeError(f"P-01 obligation results disagree with totals for {name}")
    validate_workload_membership(payload, fixtures)
    return fixtures


def validate_workload_membership(manifest: dict, fixtures: dict) -> None:
    """Require a closed, one-to-one identity map from fixture rows to workload records."""
    workloads = manifest.get("workloads")
    if not isinstance(workloads, dict) or not workloads:
        raise RuntimeError("P-01 workload identity inventory is missing")

    members_seen: dict[str, str] = {}
    for workload_name, workload in workloads.items():
        if not isinstance(workload_name, str) or not workload_name or not isinstance(workload, dict):
            raise RuntimeError("P-01 workload identity record is malformed")
        members = workload.get("members")
        if (not isinstance(members, list) or not members
                or any(not isinstance(member, str) or not member for member in members)
                or len(set(members)) != len(members)):
            raise RuntimeError(f"P-01 workload identity members are missing or duplicated for {workload_name}")
        if not isinstance(workload.get("shape"), str) or not workload["shape"]:
            raise RuntimeError(f"P-01 workload shape identity is missing for {workload_name}")
        if not isinstance(workload.get("source_relation"), str) or not workload["source_relation"]:
            raise RuntimeError(f"P-01 workload source identity is missing for {workload_name}")
        for member in members:
            if member not in fixtures:
                raise RuntimeError(f"P-01 workload {workload_name} names missing fixture {member}")
            if member in members_seen:
                raise RuntimeError(f"P-01 fixture {member} belongs to multiple workload identities")
            if fixtures[member].get("workload") != workload_name:
                raise RuntimeError(f"P-01 fixture {member} disagrees with workload identity {workload_name}")
            members_seen[member] = workload_name

    if set(members_seen) != set(fixtures):
        missing = sorted(set(fixtures) - set(members_seen))
        extra = sorted(set(members_seen) - set(fixtures))
        raise RuntimeError(f"P-01 workload identity inventory does not cover fixtures; missing={missing}, extra={extra}")


EXPECTED_OUTCOMES = {name: row["expected_outcome"]
                     for name, row in load_sentinel_manifest().items()}
def identity(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def source_line_count(path: Path) -> int:
    data = path.read_bytes()
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def validate_workload_identities(sentinels: dict) -> dict:
    """Bind every manifest row to the fixed name/path table and current fixture bytes."""
    if set(sentinels) != {name for name, _ in FIXTURES}:
        raise RuntimeError("P-01 fixtures do not match the versioned sentinel manifest")
    fixture_ids = {name: identity(path) for name, path in FIXTURES}
    for name, path in FIXTURES:
        sentinel = sentinels[name]
        if sentinel.get("path") != str(path.relative_to(ROOT)):
            raise RuntimeError(f"P-01 sentinel path changed for {name}")
        if (sentinel.get("sha256") != fixture_ids[name]["sha256"]
                or sentinel.get("size_bytes") != fixture_ids[name]["size_bytes"]
                or sentinel.get("source_lines") != source_line_count(path)):
            raise RuntimeError(f"P-01 workload identity changed for {name}; review and version the sentinel")
    return fixture_ids


def build_identity(binary: Path) -> dict:
    """Read and verify the adjacent build manifest so measurements name the exact toolchain."""
    manifest_path = Path(str(binary) + ".manifest.json")
    digest_path = Path(str(manifest_path) + ".sha256")
    if not manifest_path.is_file() or not digest_path.is_file():
        return {"available": False, "reason": "build manifest or checksum is missing"}
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    recorded_sha256 = digest_path.read_text(encoding="ascii").strip()
    try:
        manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"build manifest is invalid JSON: {error}") from error
    binary_sha256 = identity(binary)["sha256"]
    if recorded_sha256 != manifest_sha256:
        raise RuntimeError("build manifest checksum does not match its sidecar")
    if manifest.get("binary", {}).get("sha256") != binary_sha256:
        raise RuntimeError("build manifest does not describe the selected proof binary")
    proof = manifest.get("proof")
    frontend = manifest.get("frontend")
    compiler = manifest.get("compiler")
    runtime = manifest.get("runtime")
    if not isinstance(proof, dict) or not proof.get("source_tree_sha256"):
        raise RuntimeError("build manifest is missing the proof source identity")
    if not isinstance(frontend, dict) or not frontend.get("revision") or not frontend.get("tree"):
        raise RuntimeError("build manifest is missing the frontend revision/tree identity")
    if not isinstance(compiler, dict) or not isinstance(compiler.get("product"), dict) \
            or not compiler["product"].get("sha256"):
        raise RuntimeError("build manifest is missing the compiler product identity")
    if not isinstance(runtime, dict) or not runtime.get("sha256"):
        raise RuntimeError("build manifest is missing the runtime identity")
    for key in ("target", "optimization", "compile_mode"):
        if not manifest.get(key):
            raise RuntimeError(f"build manifest is missing {key} identity")
    return {"available": True, "path": str(manifest_path), "sha256": manifest_sha256,
            "build_identity": manifest.get("build_identity"),
            "proof": proof, "frontend": frontend,
            "compiler": compiler, "runtime": runtime,
            "target": manifest.get("target"), "optimization": manifest.get("optimization"),
            "compile_mode": manifest.get("compile_mode")}


def validate_probe_identity(probe: dict, build: dict, binary: Path,
                            replay_build: dict, replay_binary: Path) -> None:
    """Refuse a cohort pin made by a different proof/toolchain artifact."""
    coherence_paths = (
        ("proof", "head"), ("proof", "source_tree_sha256"),
        ("frontend", "revision"), ("frontend", "tree"),
        ("compiler", "source_revision"), ("compiler", "product.sha256"),
        ("runtime", "sha256"),
    )
    for section, field in coherence_paths:
        left = build
        right = replay_build
        for part in (section, *field.split(".")):
            left = left.get(part) if isinstance(left, dict) else None
            right = right.get(part) if isinstance(right, dict) else None
        if left != right:
            raise RuntimeError(f"P-01 proof/replay artifact provenance differs for {section}.{field}")
    for key in ("target", "optimization", "compile_mode"):
        if build.get(key) != replay_build.get(key):
            raise RuntimeError(f"P-01 proof/replay artifact provenance differs for {key}")
    actual = {
        "proof_head": build["proof"].get("head"),
        "proof_source_tree_sha256": build["proof"].get("source_tree_sha256"),
        "compiler_source_revision": build["compiler"].get("source_revision"),
        "compiler_product_sha256": build["compiler"]["product"].get("sha256"),
        "frontend_tree": build["frontend"].get("tree"),
        "runtime_sha256": build["runtime"].get("sha256"),
        "proof_binary_sha256": identity(binary)["sha256"],
        "replay_binary_sha256": identity(replay_binary)["sha256"],
        "target": build.get("target"),
        "optimization": build.get("optimization"),
        "compile_mode": build.get("compile_mode"),
        "generation": build.get("build_identity"),
    }
    for key, observed in actual.items():
        if probe.get(key) != observed:
            raise RuntimeError(f"P-01 semantic probe provenance mismatch for {key}")
