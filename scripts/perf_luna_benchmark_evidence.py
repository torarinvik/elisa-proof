"""Compact semantic outcome projections for durable paired benchmark records."""

from __future__ import annotations

import hashlib
import json


def _object(raw: bytes, label: str) -> dict:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} output is not valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} output is not a JSON object")
    return value


def _sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def semantic_outcome_projection(proof: bytes, package: bytes, replay: bytes) -> dict:
    """Keep reviewable obligation, trust, package, and replay outcomes next to timing data."""
    proof_report = _object(proof, "proof")
    package_report = _object(package, "package export")
    replay_report = _object(replay, "standalone replay")
    goals = proof_report.get("goals")
    summary = proof_report.get("summary")
    if not isinstance(goals, list) or not isinstance(summary, dict):
        raise RuntimeError("proof output lacks its obligation inventory or summary")
    replay_counts = proof_report.get("replay")
    proof_trust = proof_report.get("trust")
    package_source = package_report.get("source")
    package_theorems = package_report.get("theorems")
    replay_summary = replay_report.get("summary", {})
    replay_trust = replay_report.get("trust")
    if not all(isinstance(value, dict) for value in
               (replay_counts, proof_trust, package_source, replay_trust, replay_summary)):
        raise RuntimeError("proof/package/replay output lacks trust or replay records")
    if not isinstance(package_theorems, list):
        raise RuntimeError("package output lacks theorem inventory")
    assumptions = proof_trust.get("trusted_assumptions")
    boundary_facts = proof_trust.get("trusted_boundary_facts")
    kernel_replayed = proof_trust.get("kernel_replayed_certificates")
    if (not isinstance(assumptions, list) or type(boundary_facts) is not int
            or type(kernel_replayed) is not int):
        raise RuntimeError("proof trust report lacks its assumption or boundary summary")
    return {
        "proof_status": proof_report.get("status"),
        "proof_summary": summary,
        "obligation_count": len(goals),
        "obligation_inventory_sha256": _sha256(goals),
        "proof_trust": {
            "trusted_assumptions": assumptions,
            "trusted_boundary_facts": boundary_facts,
            "kernel_replayed_certificates": kernel_replayed,
            "full_projection_sha256": _sha256(proof_trust),
        },
        "proof_replay": replay_counts,
        "package_admissible": package_source.get("admissible"),
        "package_theorem_count": len(package_theorems),
        "package_theorem_inventory_sha256": _sha256(package_theorems),
        "standalone_replay_status": replay_report.get("status"),
        "standalone_replay_summary": replay_summary,
        "standalone_replay_trust": replay_trust,
    }
