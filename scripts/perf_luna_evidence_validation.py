"""Offline integrity checks for committed paired proof-performance evidence."""

from __future__ import annotations

import math
import hashlib
import json
import re

from perf_build_provenance import require_compatible_products, shared_product_context


SHA256 = re.compile(r"[0-9a-f]{64}\Z")
GIT_OBJECT = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
GIT_REVISION_PREFIX = re.compile(r"[0-9a-f]{7,64}\Z")
IDENTITY_FIELDS = (
    "proof.source_tree_sha256", "frontend.revision", "frontend.tree",
    "compiler.stage", "compiler.stage1_revision", "compiler.source_revision",
    "compiler.source_dirty", "compiler.product.sha256", "compiler.executable.sha256",
    "runtime.sha256", "profile_hooks.sha256", "target", "optimization",
    "compile_mode", "compiler_flags",
)
MEASUREMENT_PHASES = ("proof", "package_export", "standalone_replay")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _valid_identity(value: object, label: str) -> None:
    _require(isinstance(value, dict), f"{label} identity is missing")
    _require(isinstance(value.get("sha256"), str)
             and SHA256.fullmatch(value["sha256"]) is not None,
             f"{label} SHA-256 is invalid")
    size = value.get("size_bytes")
    _require(type(size) is int and size > 0, f"{label} size is invalid")


def _finite_nonnegative(value: object, label: str) -> None:
    _require(type(value) in (float, int) and math.isfinite(value) and value >= 0,
             f"{label} must be a finite nonnegative number")


def validate_report(report: object) -> dict:
    """Validate report provenance, paired semantic outcomes, and measured sample completeness."""
    _require(isinstance(report, dict), "benchmark report must be an object")
    _require(report.get("schema") == "elisa-proof-perf-luna-v4",
             "unsupported benchmark evidence schema")
    rounds, warmups = report.get("rounds"), report.get("warmup_rounds")
    _require(type(rounds) is int and rounds > 0, "paired round count is missing")
    _require(type(warmups) is int and warmups >= 0, "warmup count is invalid")
    _require(report.get("measurement_order") == "alternating-baseline-candidate",
             "measurement order is not paired and alternating")

    contexts = report.get("build_context")
    sources = report.get("source_tree_sha256")
    _require(isinstance(contexts, dict) and set(contexts) == {"baseline", "candidate"},
             "both build contexts are required")
    _require(isinstance(sources, dict) and set(sources) == {"baseline", "candidate"},
             "both proof source digests are required")
    for arm in ("baseline", "candidate"):
        context = contexts[arm]
        _require(isinstance(context, dict), f"{arm} build context is malformed")
        for field in IDENTITY_FIELDS:
            optional = {"compiler.source_revision", "profile_hooks.sha256"}
            _require(field in context and (context[field] is not None or field in optional),
                     f"{arm} provenance lacks {field}")
        for field in ("proof.source_tree_sha256", "compiler.product.sha256",
                      "compiler.executable.sha256", "runtime.sha256"):
            _require(isinstance(context[field], str) and SHA256.fullmatch(context[field]) is not None,
                     f"{arm} provenance has invalid digest {field}")
        for field in ("frontend.revision", "frontend.tree"):
            _require(isinstance(context[field], str)
                     and GIT_OBJECT.fullmatch(context[field]) is not None,
                     f"{arm} provenance has invalid revision {field}")
        _require(isinstance(context["compiler.stage1_revision"], str)
                 and GIT_REVISION_PREFIX.fullmatch(context["compiler.stage1_revision"]) is not None,
                 f"{arm} provenance has invalid revision compiler.stage1_revision")
        _require(context["compiler.source_dirty"] is False,
                 f"{arm} compiler source is not clean")
        _require(context["proof.source_tree_sha256"] == sources[arm],
                 f"{arm} source digest disagrees with build context")
        _require(isinstance(sources[arm], str) and SHA256.fullmatch(sources[arm]) is not None,
                 f"{arm} proof source digest is invalid")
    _require({key: contexts["baseline"][key] for key in IDENTITY_FIELDS
              if key != "proof.source_tree_sha256"}
             == {key: contexts["candidate"][key] for key in IDENTITY_FIELDS
                 if key != "proof.source_tree_sha256"},
             "paired products use different compiler/frontend/runtime/target identities")

    binaries = report.get("binaries")
    manifest_texts = report.get("build_manifests")
    _require(isinstance(binaries, dict) and set(binaries) == {"baseline", "candidate"},
             "both binary identity records are required")
    _require(isinstance(manifest_texts, dict)
             and set(manifest_texts) == {"baseline", "candidate"},
             "embedded build manifests are required for provenance revalidation")
    for arm in ("baseline", "candidate"):
        record = binaries[arm]
        _require(isinstance(record, dict), f"{arm} binary identity record is malformed")
        for product in ("proof", "replay", "proof_manifest", "replay_manifest"):
            _valid_identity(record.get(product + "_identity"), f"{arm}/{product}")
        decoded = {}
        for role in ("proof", "replay"):
            raw = manifest_texts[arm].get(role)
            _require(isinstance(raw, str), f"{arm}/{role} manifest text is missing")
            encoded = raw.encode("utf-8")
            manifest_identity = record[role + "_manifest_identity"]
            _require(hashlib.sha256(encoded).hexdigest() == manifest_identity["sha256"]
                     and len(encoded) == manifest_identity["size_bytes"],
                     f"{arm}/{role} embedded manifest digest does not match its identity")
            try:
                decoded[role] = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ValueError(f"{arm}/{role} embedded manifest is invalid JSON") from error
            _require(isinstance(decoded[role], dict), f"{arm}/{role} manifest is not an object")
            _require(decoded[role].get("binary", {}).get("sha256")
                     == record[role + "_identity"]["sha256"],
                     f"{arm}/{role} manifest does not identify measured executable")
            _require(shared_product_context(decoded[role]) == contexts[arm],
                     f"{arm}/{role} manifest disagrees with recorded build context")
        require_compatible_products(decoded["proof"], decoded["replay"], arm)

    fixtures = report.get("fixtures")
    selected = report.get("selected_fixtures")
    _require(isinstance(fixtures, list) and bool(fixtures), "no measured fixture records")
    names = [item.get("fixture") if isinstance(item, dict) else None for item in fixtures]
    _require(isinstance(selected, list) and names == selected and len(set(names)) == len(names),
             "selected fixture list does not match unique evidence rows")
    for item in fixtures:
        source = item.get("source")
        _valid_identity(source, f"{item['fixture']} source")
        _require(item.get("semantic_outputs_identical") is True,
                 f"{item['fixture']} lacks semantic parity")
        _require(item.get("expected_status") in ("proved", "failed")
                 and type(item.get("expected_exit")) is int,
                 f"{item['fixture']} has no pinned expected outcome")
        _require(item["expected_exit"] == (0 if item["expected_status"] == "proved" else 1),
                 f"{item['fixture']} expected status and exit disagree")
        outcomes = item.get("semantic_outcomes")
        _require(isinstance(outcomes, dict)
                 and set(outcomes) == {"baseline", "candidate"}
                 and outcomes["baseline"] == outcomes["candidate"],
                 f"{item['fixture']} obligation/replay/trust outcomes differ")
        outcome = outcomes["baseline"]
        _require(outcome.get("proof_status") == item["expected_status"],
                 f"{item['fixture']} proof status differs from expected")
        _require(type(outcome.get("obligation_count")) is int
                 and outcome["obligation_count"] >= 0
                 and isinstance(outcome.get("proof_trust"), dict)
                 and isinstance(outcome.get("proof_replay"), dict),
                 f"{item['fixture']} proof obligation/trust evidence is invalid")
        proof_trust = outcome["proof_trust"]
        _require(isinstance(proof_trust.get("trusted_assumptions"), list)
                 and type(proof_trust.get("trusted_boundary_facts")) is int
                 and proof_trust["trusted_boundary_facts"] >= 0
                 and type(proof_trust.get("kernel_replayed_certificates")) is int
                 and SHA256.fullmatch(proof_trust.get("full_projection_sha256", "")) is not None,
                 f"{item['fixture']} proof trust summary is invalid")
        for field in ("obligation_inventory_sha256", "package_theorem_inventory_sha256"):
            _require(isinstance(outcome.get(field), str)
                     and SHA256.fullmatch(outcome[field]) is not None,
                     f"{item['fixture']} {field} is invalid")
        _require(outcome.get("standalone_replay_status")
                 == ("replayed" if outcome.get("package_theorem_count", 0) > 0 else "rejected"),
                 f"{item['fixture']} standalone replay status disagrees with package")
        _require(isinstance(outcome.get("standalone_replay_trust"), dict)
                 and outcome["standalone_replay_trust"].get("kernel") == "checked",
                 f"{item['fixture']} standalone replay trust boundary is invalid")
        digests = item.get("semantic_output_sha256")
        _require(isinstance(digests, dict) and set(digests) == {"baseline", "candidate"},
                 f"{item['fixture']} lacks paired semantic digests")
        for phase in ("proof", "export", "replay"):
            left, right = digests["baseline"].get(phase), digests["candidate"].get(phase)
            _require(isinstance(left, str) and SHA256.fullmatch(left) is not None
                     and left == right,
                     f"{item['fixture']}/{phase} semantic outputs differ or have invalid digests")
        workload = item.get("semantic_workload")
        _require(isinstance(workload, dict)
                 and workload.get("baseline") == workload.get("candidate"),
                 f"{item['fixture']} obligation/replay/trust metrics differ")
        metrics = workload["baseline"]
        _require(isinstance(metrics, dict) and metrics.get("complete") is True
                 and metrics.get("replay_gaps") == 0
                 and metrics.get("certificate_count") == metrics.get("replayed_count"),
                 f"{item['fixture']} proof/replay outcomes are incomplete")
        _require(metrics.get("obligations") == outcome["obligation_count"],
                 f"{item['fixture']} semantic obligation count is inconsistent")
        proof_replay = outcome["proof_replay"]
        _require(proof_replay.get("certificates") == metrics.get("certificate_count")
                 and proof_replay.get("replayed") == metrics.get("replayed_count")
                 and proof_replay.get("gaps") == metrics.get("replay_gaps")
                 and proof_trust.get("kernel_replayed_certificates") == metrics.get("replayed_count"),
                 f"{item['fixture']} proof trust/replay totals are inconsistent")
        replay_summary = outcome["standalone_replay_summary"]
        _require(isinstance(replay_summary, dict)
                 and (outcome["package_theorem_count"] == 0
                      or replay_summary.get("theorems") == outcome["package_theorem_count"]
                      and replay_summary.get("not_replayed") == 0),
                 f"{item['fixture']} standalone replay does not cover exported theorems")
        for field in MEASUREMENT_PHASES:
            arms = item.get(field)
            _require(isinstance(arms, dict) and set(arms) == {"baseline", "candidate"},
                     f"{item['fixture']}/{field} paired measurements are missing")
            for arm in ("baseline", "candidate"):
                sample = arms[arm]
                _require(isinstance(sample, dict) and sample.get("rounds") == rounds,
                         f"{item['fixture']}/{field}/{arm} sample count is incomplete")
                for metric in ("p50_wall_seconds", "p95_wall_seconds", "minimum_wall_seconds",
                               "maximum_wall_seconds", "wall_spread_seconds"):
                    _finite_nonnegative(sample.get(metric), f"{item['fixture']}/{field}/{arm}/{metric}")
                for metric in ("p50_user_cpu_seconds", "p50_system_cpu_seconds"):
                    if sample.get(metric) is not None:
                        _finite_nonnegative(sample[metric], f"{item['fixture']}/{field}/{arm}/{metric}")
                rss = sample.get("peak_rss_kib")
                _require(rss is None or (type(rss) is int and rss > 0),
                         f"{item['fixture']}/{field}/{arm} peak RSS is invalid")
        raw_samples = item.get("paired_samples")
        _require(isinstance(raw_samples, dict)
                 and set(raw_samples) == {"proof", "export", "replay"},
                 f"{item['fixture']} per-round paired samples are missing")
        for phase, arms in raw_samples.items():
            _require(isinstance(arms, dict) and set(arms) == {"baseline", "candidate"},
                     f"{item['fixture']}/{phase} per-arm raw samples are missing")
            for arm in ("baseline", "candidate"):
                samples = arms[arm]
                _require(isinstance(samples, list) and len(samples) == rounds,
                         f"{item['fixture']}/{phase}/{arm} raw sample count is incomplete")
                _require([sample.get("pair_index") for sample in samples]
                         == list(range(1, rounds + 1)),
                         f"{item['fixture']}/{phase}/{arm} pair indexes are invalid")
                for index, sample in enumerate(samples):
                    _finite_nonnegative(sample.get("wall_seconds"),
                                        f"{item['fixture']}/{phase}/{arm}/{index}/wall")
                    for metric in ("user_cpu_seconds", "system_cpu_seconds"):
                        if sample.get(metric) is not None:
                            _finite_nonnegative(sample[metric],
                                                f"{item['fixture']}/{phase}/{arm}/{index}/{metric}")
                    rss = sample.get("peak_rss_kib")
                    _require(rss is None or (type(rss) is int and rss > 0),
                             f"{item['fixture']}/{phase}/{arm}/{index} RSS is invalid")

    return {"valid": True, "fixtures": len(fixtures), "rounds": rounds,
            "semantic_parity": True, "speedup_claim": "none-asserted"}
