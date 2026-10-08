#!/usr/bin/env python3
"""Run the refusal census over all examples and dogfood proof units.

The checked-in census is stable: it contains counts and refusal buckets, never wall-clock data.
Per-input timings live in a separate measurements sidecar for performance investigations.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from report_cache import effective_cpus
from report_exit_status import expected_exit as report_expected_exit

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof")).resolve()
DOGFOOD_SOURCES = ("src/proof/kernel_core.elisa",)
# One proof run per core; ELISA_PROOF_CENSUS_JOBS overrides (e.g. to share a busy host).
DEFAULT_WORKERS = int(os.environ.get("ELISA_PROOF_CENSUS_JOBS", "0")) or effective_cpus()


def input_key(path):
    relative = path.relative_to(ROOT).as_posix()
    return path.name if relative.startswith("examples/") else relative


def census_report(data):
    """Retain census fields after the complete report has passed validation.

    Completed worker futures can wait behind a slow input. Do not let those
    futures retain certificate arenas, traces or source graphs for every input.
    Presence (including explicit null) of finding fields is preserved because
    the refusal and diagnostic buckets distinguish missing fields from null.
    """
    result = {
        "status": data["status"],
        "verification_state": data["verification_state"],
        "summary": {key: data["summary"][key] for key in ("proven", "obligations")},
        "findings": [
            {key: finding[key] for key in ("refusal_gate", "kind", "message") if key in finding}
            for finding in data["findings"]
        ],
    }
    replay = data.get("replay")
    if isinstance(replay, dict) and "gaps" in replay:
        result["replay"] = {"gaps": replay["gaps"]}
    return result


def run(path, timeout):
    """Return a validated census projection, elapsed seconds and failure category."""
    started = time.monotonic()
    try:
        result = subprocess.run(
            [str(BINARY), "--json", str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return data_key(path), None, time.monotonic() - started, "invalid-json"
        if not isinstance(data, dict) or not isinstance(data.get("summary"), dict):
            return data_key(path), None, time.monotonic() - started, "invalid-report"
        try:
            expected_exit = report_expected_exit(data)
        except ValueError:
            return data_key(path), None, time.monotonic() - started, "invalid-result-lattice"
        if result.returncode != expected_exit:
            return data_key(path), None, time.monotonic() - started, "exit-status-mismatch"
        summary = data["summary"]
        if (type(summary.get("proven")) is not int or type(summary.get("obligations")) is not int
                or summary["proven"] < 0 or summary["obligations"] < summary["proven"]):
            return data_key(path), None, time.monotonic() - started, "invalid-summary"
        if not isinstance(data.get("findings"), list) or not all(
            isinstance(finding, dict) for finding in data["findings"]
        ):
            return data_key(path), None, time.monotonic() - started, "invalid-findings"
        return data_key(path), census_report(data), time.monotonic() - started, None
    except subprocess.TimeoutExpired:
        return data_key(path), None, time.monotonic() - started, "timeout"
    except OSError:
        return data_key(path), None, time.monotonic() - started, "execution-error"


def data_key(path):
    return input_key(path)


def previous_seconds(path):
    """Per-input seconds from an earlier measurements sidecar, or {} when there is none."""
    try:
        files = json.loads(Path(path).read_text()).get("files", {})
    except (OSError, ValueError, AttributeError):
        return {}
    return {name: entry.get("seconds", 0) for name, entry in files.items() if isinstance(entry, dict)}


def tree_sha256(root):
    digest = hashlib.sha256()
    for directory, subdirectories, files in os.walk(root):
        subdirectories.sort()
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def summarize(results, example_count, dogfood_count, run_date, toolchain):
    gates = Counter()
    diagnostics = Counter()
    files = {}
    unreadable = []
    unreadable_reasons = {}
    proven = obligations = 0

    for name in sorted(results):
        entry = results[name]
        data = entry["report"]
        if data is None:
            unreadable.append(name)
            unreadable_reasons[name] = entry["error"] or "unreadable"
            continue

        summary = data["summary"]
        file_gates = set()
        file_diagnostics = set()
        for finding in data["findings"]:
            gate = finding.get("refusal_gate")
            if gate:
                gates[gate] += 1
                file_gates.add(gate)
            else:
                # A finding without an attempted goal is diagnostic, not a first-refusal gate.
                diagnostic = f"{finding.get('kind', 'unknown')}: {finding.get('message', '')}"
                diagnostics[diagnostic] += 1
                file_diagnostics.add(diagnostic)

        file_proven = summary["proven"]
        file_obligations = summary["obligations"]
        proven += file_proven
        obligations += file_obligations
        files[name] = {
            "proven": file_proven,
            "obligations": file_obligations,
            "gates": sorted(file_gates),
            "diagnostics": sorted(file_diagnostics),
        }

    report = {
        "schema": "elisa-proof-refusal-census-v1",
        "date": run_date,
        "examples": example_count,
        "dogfood_units": dogfood_count,
        "proven": proven,
        "obligations": obligations,
        "unreadable": unreadable,
        "unreadable_reasons": unreadable_reasons,
        "gates": dict(sorted(gates.items(), key=lambda item: (-item[1], item[0]))),
        "diagnostics": dict(sorted(diagnostics.items(), key=lambda item: (-item[1], item[0]))),
        "files": files,
    }
    if toolchain is not None:
        report["toolchain"] = toolchain
    return report


def measurements(results, run_date, toolchain):
    per_file = {
        name: {"seconds": round(entry["seconds"], 2)}
        for name, entry in sorted(results.items())
    }
    slowest = sorted(per_file, key=lambda name: (-per_file[name]["seconds"], name))[:10]
    result = {"schema": "elisa-proof-census-measurements-v1", "date": run_date, "files": per_file,
              "slowest": slowest}
    if toolchain is not None:
        result["toolchain"] = toolchain
    return result


def toolchain_identity():
    manifest_path = Path(str(BINARY) + ".manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read proof build manifest {manifest_path}: {error}")
    compiler = manifest.get("compiler", {})
    frontend = manifest.get("frontend", {})
    proof = manifest.get("proof", {})
    binary = manifest.get("binary", {})
    expected_revision = os.environ.get("ELISA_COMPILER_REV", "").strip()
    if not expected_revision:
        expected_revision = (ROOT / "ELISA_COMPILER_REV").read_text().strip()
    compiler_revision = compiler.get("source_revision")
    frontend_revision = frontend.get("revision")
    current_source_digest = tree_sha256(ROOT / "src")
    if proof.get("source_tree_sha256") != current_source_digest:
        raise RuntimeError("proof source tree changed since the proof binary was built")
    if expected_revision and (
        not compiler_revision or not compiler_revision.startswith(expected_revision)
        or frontend_revision != expected_revision
    ):
        raise RuntimeError(
            f"compiler/frontend provenance does not match ELISA_COMPILER_REV {expected_revision}"
        )
    if compiler.get("stage") != "stage1":
        raise RuntimeError(f"refusal census requires the pinned Stage1 compiler, got {compiler.get('stage')!r}")
    try:
        digest = hashlib.sha256(BINARY.read_bytes()).hexdigest()
    except OSError as error:
        raise RuntimeError(f"cannot hash proof binary {BINARY}: {error}")
    if digest != binary.get("sha256"):
        raise RuntimeError("proof binary SHA-256 does not match its build manifest")
    return {
        "proof_binary_sha256": binary.get("sha256"),
        "proof_head": proof.get("head"),
        "proof_sources_dirty_at_build": proof.get("source_dirty"),
        "compiler_stage": compiler.get("stage"),
        "compiler_revision": compiler.get("source_revision"),
        "compiler_product_sha256": compiler.get("product", {}).get("sha256"),
        "frontend_revision": frontend.get("revision"),
    }


def render_markdown(report):
    lines = [
        "# Refusal census",
        "",
        f"Census date: {report['date']} (UTC).",
        "",
        f"{report['examples']} examples and {report['dogfood_units']} dogfood proof units; "
        f"{report['proven']}/{report['obligations']} obligations proven.",
        "",
        f"Unreadable inputs: {len(report['unreadable'])}.",
        "",
        "| Count | First refusal gate |",
        "| ---: | --- |",
    ]
    lines.extend(
        f"| {count} | {gate.replace('|', '/')} |"
        for gate, count in report["gates"].items()
    )
    lines += ["", "## Non-goal diagnostics", "", "| Count | Diagnostic |", "| ---: | --- |"]
    lines.extend(
        f"| {count} | {diagnostic.replace('|', '/')} |"
        for diagnostic, count in report["diagnostics"].items()
    )
    if report["unreadable"]:
        lines += ["", "## Unreadable inputs", ""]
        lines.extend(f"- `{name}`: {report['unreadable_reasons'][name]}" for name in report["unreadable"])
    if report.get("toolchain"):
        identity = report["toolchain"]
        lines += [
            "",
            "## Toolchain provenance",
            "",
            f"Proof binary SHA-256: `{identity.get('proof_binary_sha256')}`; "
            f"compiler stage: `{identity.get('compiler_stage')}`; "
            f"compiler revision: `{identity.get('compiler_revision')}`; "
            f"proof source HEAD: `{identity.get('proof_head')}`.",
        ]
    return "\n".join(lines) + "\n"


def render_measurements_markdown(data):
    lines = [
        "# Refusal census measurements",
        "",
        f"Per-input wall time from the census run on {data['date']} UTC. Timings are load-dependent "
        "and are intentionally excluded from the deterministic census.",
        "",
        "| Seconds | Input |",
        "| ---: | --- |",
    ]
    lines.extend(
        f"| {data['files'][name]['seconds']:.2f} | `{name}` |"
        for name in data["slowest"]
    )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", nargs="?", type=Path, default=ROOT / "docs/census")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--retry-timeout-seconds", type=int, default=600)
    parser.add_argument("--retry-unreadable", action="store_true",
                        help="retry timed-out/invalid inputs serially with the longer retry timeout")
    arguments = parser.parse_args()
    if arguments.workers < 1 or arguments.timeout_seconds < 1 or arguments.retry_timeout_seconds < 1:
        parser.error("workers and timeouts must be positive")
    if not BINARY.is_file() or not os.access(BINARY, os.X_OK):
        parser.error(f"proof binary is not executable: {BINARY}")

    examples = sorted((ROOT / "examples").glob("*.elisa"))
    dogfood = [ROOT / source for source in DOGFOOD_SOURCES]
    missing_dogfood = [path.relative_to(ROOT).as_posix() for path in dogfood if not path.is_file()]
    if missing_dogfood:
        parser.error(f"dogfood source is missing: {', '.join(missing_dogfood)}")
    paths = examples + dogfood
    if len({data_key(path) for path in paths}) != len(paths):
        parser.error("duplicate census input key")

    try:
        identity = toolchain_identity()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        parser.error(str(error))

    # Longest inputs first (by the committed timing sidecar) so the slow tail starts immediately;
    # census_diff writes to a scratch dir, so always read the committed sidecar.
    previous = previous_seconds(ROOT / "docs/census/measurements.json")
    ordered = sorted(paths, key=lambda path: -previous.get(data_key(path), 0))
    with ThreadPoolExecutor(max_workers=arguments.workers) as pool:
        attempts = list(pool.map(lambda path: run(path, arguments.timeout_seconds), ordered))
    results = {
        name: {"report": data, "seconds": seconds, "error": error}
        for name, data, seconds, error in attempts
    }

    if arguments.retry_unreadable:
        retry_paths = {data_key(path): path for path in paths if results[data_key(path)]["report"] is None}
        with ThreadPoolExecutor(max_workers=arguments.workers) as pool:
            retried = list(pool.map(lambda name: run(retry_paths[name], arguments.retry_timeout_seconds),
                                    sorted(retry_paths)))
        for name, data, seconds, error in retried:
            results[name]["report"] = data
            results[name]["seconds"] += seconds
            results[name]["error"] = error

    run_date = datetime.now(timezone.utc).date().isoformat()
    try:
        final_identity = toolchain_identity()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    if identity != final_identity:
        parser.error("proof binary, sources, or compiler changed during the census; refusing to publish mixed results")
    report = summarize(results, len(examples), len(dogfood), run_date, identity)
    measurement_report = measurements(results, run_date, identity)
    output_dir = arguments.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "census.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (output_dir / "census.md").write_text(render_markdown(report))
    (output_dir / "measurements.json").write_text(json.dumps(measurement_report, indent=1, sort_keys=True) + "\n")
    (output_dir / "measurements.md").write_text(render_measurements_markdown(measurement_report))
    print(f"census: {report['proven']}/{report['obligations']} proven across "
          f"{report['examples']} examples and {report['dogfood_units']} dogfood units, "
          f"{len(report['gates'])} refusal buckets, {len(report['unreadable'])} unreadable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
