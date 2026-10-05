#!/usr/bin/env python3
"""Summarize allocation lifecycle records in memory benchmark JSON artifacts.

The output deliberately keeps logical live bytes, backing capacity, and capture
quality separate. It does not infer RSS or allocation-site identity from these
records.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MAX_CAPTURE_BYTES = 128 * 1024 * 1024
MAX_WORKLOADS = 10_000
MAX_REPETITIONS = 100_000


class CaptureError(ValueError):
    pass


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CaptureError(f"{label} must be a nonnegative integer")
    return value


def summarize_allocation_captures(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaptureError("allocation_captures must be an object")
    if len(value) > MAX_WORKLOADS:
        raise CaptureError(f"allocation_captures exceeds {MAX_WORKLOADS} workloads")

    workloads: list[dict[str, Any]] = []
    for name, records in sorted(value.items()):
        if not isinstance(name, str) or not name:
            raise CaptureError("workload names must be nonempty strings")
        if not isinstance(records, list) or len(records) > MAX_REPETITIONS:
            raise CaptureError(f"{name}: repetitions must be an array of at most {MAX_REPETITIONS}")
        runs = []
        for index, record in enumerate(records):
            label = f"{name}[{index}]"
            if not isinstance(record, dict):
                raise CaptureError(f"{label} must be an object")
            complete = record.get("capture_complete")
            if not isinstance(complete, bool):
                raise CaptureError(f"{label}.capture_complete must be a boolean")
            dropped = _nonnegative_int(record.get("allocation_events_dropped"),
                                       f"{label}.allocation_events_dropped")
            counts = record.get("event_counts")
            metrics = record.get("metrics")
            if not isinstance(counts, dict) or not isinstance(metrics, dict):
                raise CaptureError(f"{label} requires event_counts and metrics objects")
            event_counts = {key: _nonnegative_int(count, f"{label}.event_counts.{key}")
                            for key, count in sorted(counts.items())}
            metric_names = (
                "peak_logical_live_bytes", "logical_live_bytes_at_capture_end",
                "peak_observed_backing_capacity_bytes",
                "observed_backing_capacity_at_capture_end_bytes",
                "max_retained_backing_capacity_after_reset_bytes",
                "peak_retained_capacity_on_reuse_bytes",
            )
            selected_metrics = {
                key: _nonnegative_int(metrics[key], f"{label}.metrics.{key}")
                for key in metric_names if key in metrics
            }
            lifetime = record.get("lifetime_status", "unavailable")
            if not isinstance(lifetime, str):
                raise CaptureError(f"{label}.lifetime_status must be a string")
            quality = "complete" if complete and dropped == 0 else "incomplete"
            runs.append({
                "repetition": _nonnegative_int(record.get("repetition", index + 1),
                                                f"{label}.repetition"),
                "capture_quality": quality,
                "allocation_events_dropped": dropped,
                "event_counts": event_counts,
                "lifetime_status": lifetime,
                "metrics": selected_metrics,
            })
        workloads.append({"workload": name, "runs": runs})

    return {
        "schema_version": 1,
        "source": "allocation_captures",
        "workloads": workloads,
        "metric_notes": {
            "peak_logical_live_bytes": "captured logical live-byte high-water mark",
            "peak_observed_backing_capacity_bytes": "observed backing capacity high-water mark",
            "process_rss": "not present in these allocation records; collect separately",
            "allocation_site_identity": "not present in these records",
        },
    }


def load_artifact(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_CAPTURE_BYTES + 1)
    except OSError as exc:
        raise CaptureError(f"cannot read {path}: {exc}") from exc
    if len(raw) > MAX_CAPTURE_BYTES:
        raise CaptureError(f"artifact exceeds {MAX_CAPTURE_BYTES} bytes")
    try:
        artifact = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CaptureError(f"invalid JSON artifact: {exc}") from exc
    if not isinstance(artifact, dict) or "allocation_captures" not in artifact:
        raise CaptureError("artifact must contain allocation_captures")
    return summarize_allocation_captures(artifact["allocation_captures"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="memory benchmark JSON artifact")
    args = parser.parse_args(argv)
    try:
        result = load_artifact(args.capture)
    except CaptureError as exc:
        print(f"allocation summary: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
