#!/usr/bin/env python3
"""Summarize sampled Elisa profiler JSON captures with bounded input handling.

Sample stacks contain function names rather than function identity IDs. This
module reports name-level leaf/inclusive rankings and only attributes samples
to a definition when that name is unique within the sample's repetition.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


MAX_CAPTURE_BYTES = 128 * 1024 * 1024
PROFILER_SCHEMA_VERSION = 2
MAX_IDENTITY_ID = (1 << 64) - 1
MAX_SAMPLES = 2_000_000
MAX_FUNCTIONS = 1_000_000
MAX_LOCATIONS = 1_000_000
ATTRIBUTION_LIMITATIONS = (
    "CPU samples are stack-occupancy evidence, not exact call counts or native instruction-pointer samples.",
    "Sample stacks contain names, not identity IDs; definition attribution is omitted when a name is ambiguous within a repetition.",
    "Sample-mode captures may omit source-definition records; identical names cannot be resolved to a unique definition without those records.",
    "Runtime, foreign, and optimized-away work may be charged to the last instrumented Elisa caller.",
    "Complete CPU sampling does not verify proof or replay results; truncated program stdout prevents driver-side proof-output validation.",
)


class CaptureError(ValueError):
    """The capture is malformed or exceeds the summarizer's explicit bounds."""


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaptureError(f"{label} must be an object")
    return value


def _array(value: Any, label: str, limit: int) -> list[Any]:
    if not isinstance(value, list):
        raise CaptureError(f"{label} must be an array")
    if len(value) > limit:
        raise CaptureError(f"{label} exceeds the {limit} record limit")
    return value


def _nonnegative_int(value: Any, label: str, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CaptureError(f"{label} must be a nonnegative integer")
    return value


def _optional_bool(value: Any, label: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise CaptureError(f"{label} must be a boolean or null")
    return value


def _identity(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise CaptureError("identity_id must be an integer, decimal string, or null")
    text = str(value)
    if not text or any(char < "0" or char > "9" for char in text):
        raise CaptureError("identity_id must contain ASCII decimal digits only")
    number = int(text)
    if not 1 <= number <= MAX_IDENTITY_ID:
        raise CaptureError("identity_id must be a positive uint64")
    return str(number)


def _rank(counter: Counter[str], total: int, limit: int) -> list[dict[str, Any]]:
    return [
        {"name": name, "samples": count,
         "share_percent": round(100.0 * count / total, 4) if total else None}
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def summarize_capture(capture: Any, top: int = 20) -> dict[str, Any]:
    """Return deterministic name-level ranks and identity-aware definitions."""
    if isinstance(top, bool) or not isinstance(top, int) or not 1 <= top <= 500:
        raise CaptureError("top must be between 1 and 500")
    root = _object(capture, "capture")
    if root.get("schema_version") != PROFILER_SCHEMA_VERSION:
        raise CaptureError(
            f"unsupported or missing profiler schema_version (expected {PROFILER_SCHEMA_VERSION})")
    envelope = _object(root.get("envelope"), "envelope")
    if envelope.get("kind") != "profile":
        raise CaptureError("capture envelope kind must be 'profile'")

    summary = _object(root.get("summary"), "summary")
    run = _object(root.get("run"), "run")
    samples = _array(root.get("samples"), "samples", MAX_SAMPLES)
    functions = _array(root.get("functions", []), "functions", MAX_FUNCTIONS)
    locations = _array(root.get("locations", []), "locations", MAX_LOCATIONS)

    reported_samples = _nonnegative_int(summary.get("sample_count"), "summary.sample_count")
    missed = _nonnegative_int(summary.get("sample_missed"), "summary.sample_missed")
    setup_failed = _nonnegative_int(summary.get("sampling_setup_failed"), "summary.sampling_setup_failed")
    dropped = {
        key: _nonnegative_int(summary.get(key), f"summary.{key}")
        for key in ("dropped", "frame_dropped", "capture_bytes_dropped", "stack_overflow_entries")
    }
    dropped["total"] = sum(dropped.values())

    frame_counts: Counter[str] = Counter()
    leaf_counts: Counter[str] = Counter()
    repetition_name_counts: dict[tuple[int, str], int] = Counter()
    seen_samples = 0
    malformed_samples = 0
    for index, item in enumerate(samples):
        if not isinstance(item, dict):
            malformed_samples += 1
            continue
        stack = item.get("stack")
        repetition = item.get("repetition", 1)
        if (not isinstance(stack, str) or not stack or isinstance(repetition, bool)
                or not isinstance(repetition, int) or repetition < 1):
            malformed_samples += 1
            continue
        frames = stack.split(";")
        if any(not frame for frame in frames):
            malformed_samples += 1
            continue
        seen_samples += 1
        frame_counts.update(set(frames))
        leaf_counts[frames[-1]] += 1
        for name in set(frames):
            repetition_name_counts[(repetition, name)] += 1

    # Functions and kind=function locations preserve identity and source
    # definition metadata. Sample records themselves have no identity field.
    function_records: dict[tuple[int, str, str | None], dict[str, Any]] = {}
    for index, item in enumerate(functions):
        record = _object(item, f"functions[{index}]")
        name = record.get("function")
        repetition = record.get("repetition", 1)
        identity = _identity(record.get("identity_id"))
        if (not isinstance(name, str) or not name or isinstance(repetition, bool)
                or not isinstance(repetition, int) or repetition < 1):
            raise CaptureError(f"functions[{index}] has invalid name or repetition")
        key = (repetition, name, identity)
        function_records.setdefault(key, {"name": name, "identity_id": identity,
                                          "repetition": repetition, "samples": None,
                                          "attribution": "unavailable"})

    definitions: dict[tuple[int, str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for index, item in enumerate(locations):
        record = _object(item, f"locations[{index}]")
        if record.get("kind") != "function":
            continue
        name = record.get("function")
        repetition = record.get("repetition", 1)
        identity = _identity(record.get("identity_id"))
        if (not isinstance(name, str) or not name or isinstance(repetition, bool)
                or not isinstance(repetition, int) or repetition < 1):
            raise CaptureError(f"locations[{index}] has invalid function definition")
        definition = {
            "source": record.get("source"),
            "compiler_line": record.get("compiler_line"),
            "line": record.get("line"),
        }
        key = (repetition, name, identity)
        if definition not in definitions[key]:
            definitions[key].append(definition)
        function_records.setdefault(key, {"name": name, "identity_id": identity,
                                          "repetition": repetition, "samples": None,
                                          "attribution": "unavailable"})

    keys_by_repetition_name: dict[tuple[int, str], list[tuple[int, str, str | None]]] = defaultdict(list)
    for key in function_records:
        keys_by_repetition_name[key[:2]].append(key)
    for key, row in function_records.items():
        rep_name = key[:2]
        candidates = keys_by_repetition_name[rep_name]
        has_definition_collision_without_ids = (
            key[2] is None and len(definitions.get(key, [])) > 1)
        if len(candidates) == 1 and not has_definition_collision_without_ids:
            row["samples"] = repetition_name_counts.get(rep_name, 0)
            row["attribution"] = "unique_name_in_repetition"
        else:
            row["attribution"] = "ambiguous_name_collision"
        row["definitions"] = sorted(definitions.get(key, []),
                                    key=lambda item: (str(item["source"]),
                                                      str(item["compiler_line"]),
                                                      str(item["line"])))

    complete_value = summary.get("capture_complete")
    if not isinstance(complete_value, bool):
        raise CaptureError("summary.capture_complete must be a boolean")
    declared_repetitions = _nonnegative_int(run.get("requested_repetitions"),
                                            "run.requested_repetitions")
    completed_repetitions = _nonnegative_int(run.get("completed_repetitions"),
                                             "run.completed_repetitions")
    reasons = []
    if not complete_value:
        reasons.append("capture_incomplete")
    if reported_samples != len(samples):
        reasons.append("sample_count_mismatch")
    if malformed_samples:
        reasons.append("malformed_sample_records")
    if missed:
        reasons.append("samples_missed")
    if setup_failed:
        reasons.append("sampling_setup_failed")
    if dropped["total"]:
        reasons.append("capture_records_dropped_or_overflowed")
    if declared_repetitions and completed_repetitions < declared_repetitions:
        reasons.append("repetitions_incomplete")

    mode = run.get("collection_mode")
    if mode not in ("sample", "sampling"):
        reasons.append("capture_not_marked_as_sample_mode")

    stdout_truncated = _optional_bool(root.get("program_stdout_truncated"),
                                      "program_stdout_truncated")
    stderr_truncated = _optional_bool(root.get("program_stderr_truncated"),
                                      "program_stderr_truncated")
    if stdout_truncated:
        proof_verification_status = "unavailable_output_truncated"
    elif stdout_truncated is False:
        proof_verification_status = "not_checked_by_profile_summary"
    else:
        proof_verification_status = "output_truncation_status_unavailable"

    return {
        "schema": "elisa-proof-luna-profile-summary-v1",
        "source": root.get("source"),
        "collection_mode": mode,
        "capture": {
            "outcome": run.get("outcome"),
            "complete": complete_value,
            "requested_repetitions": declared_repetitions,
            "completed_repetitions": completed_repetitions,
            "sample_period_microseconds": _nonnegative_int(
                summary.get("sample_period_microseconds"), "summary.sample_period_microseconds"),
            "reported_samples": reported_samples,
            "retained_sample_records": len(samples),
            "valid_sample_records": seen_samples,
            "malformed_sample_records": malformed_samples,
            "sample_missed": missed,
            "sampling_setup_failed": setup_failed,
            "dropped": dropped,
            "sample_quality": "degraded" if reasons else "complete",
            "quality_reasons": reasons,
        },
        "proof_verification": {
            "status": proof_verification_status,
            "verified": False,
            "program_stdout_truncated": stdout_truncated,
            "program_stderr_truncated": stderr_truncated,
        },
        "rankings": {
            "leaf_frames": _rank(leaf_counts, seen_samples, top),
            "inclusive_frames": _rank(frame_counts, seen_samples, top),
        },
        "definitions": sorted(function_records.values(), key=lambda row: (
            -(row["samples"] if isinstance(row["samples"], int) else -1),
            row["name"], row["repetition"], row["identity_id"] or "")),
        "attribution_limitations": list(ATTRIBUTION_LIMITATIONS),
    }


def load_capture(path: Path, max_bytes: int = MAX_CAPTURE_BYTES) -> Any:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise CaptureError("max_bytes must be a positive integer")
    try:
        with path.open("rb") as stream:
            data = stream.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise CaptureError(f"capture exceeds the {max_bytes} byte limit")
        return json.loads(data)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise CaptureError(f"cannot parse capture JSON: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="native elisa-profiler JSON report")
    parser.add_argument("--top", type=int, default=20, help="rank at most this many names (1-500)")
    parser.add_argument("--max-bytes", type=int, default=MAX_CAPTURE_BYTES,
                        help=f"maximum input size (default: {MAX_CAPTURE_BYTES})")
    args = parser.parse_args(argv)
    try:
        if args.max_bytes < 1:
            raise CaptureError("max-bytes must be positive")
        result = summarize_capture(load_capture(args.capture, args.max_bytes), args.top)
    except CaptureError as error:
        print(f"profile summary: {error}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
