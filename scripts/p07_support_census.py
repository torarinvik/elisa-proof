#!/usr/bin/env python3
"""Capture declaration-level P-07 support evidence for a bounded input set.

Unlike the aggregate refusal census, this keeps unverified declaration records and
the source site of each unsupported finding so shared include bottlenecks can be
ranked by how many selected inputs they affect. It does not change checker behavior.

    ELISA_PROOF_BIN=/path/to/elisa-proof python3 scripts/p07_support_census.py \
      --out /tmp/p07-support.json --timeout-seconds 120 INPUT.elisa [INPUT2.elisa ...]
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof")).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for directory, subdirectories, files in os.walk(root):
        subdirectories.sort()
        for name in sorted(files):
            path = Path(directory) / name
            digest.update(path.relative_to(root).as_posix().encode() + b"\0")
            digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def identity() -> dict:
    manifest_path = Path(str(BINARY) + ".manifest.json")
    manifest = json.loads(manifest_path.read_text())
    proof = manifest.get("proof", {})
    compiler = manifest.get("compiler", {})
    frontend = manifest.get("frontend", {})
    binary = manifest.get("binary", {})
    source_digest = tree_sha256(ROOT / "src")
    if proof.get("source_tree_sha256") != source_digest:
        raise RuntimeError("proof source tree does not match the binary manifest")
    binary_digest = sha256(BINARY)
    if binary.get("sha256") != binary_digest:
        raise RuntimeError("proof binary does not match its build manifest")
    if compiler.get("stage") != "stage1" or not frontend.get("revision"):
        raise RuntimeError("P-07 census requires a pinned Stage1 frontend identity")
    return {
        "binary": {"path": str(BINARY), "sha256": binary_digest},
        "proof": {"head": proof.get("head"), "source_tree_sha256": source_digest},
        "frontend": {
            "revision": frontend.get("revision"),
            "tree": frontend.get("tree"),
            "compiler_revision": compiler.get("source_revision"),
        },
        "target": manifest.get("target"),
        "optimization": manifest.get("optimization"),
        "compile_mode": manifest.get("compile_mode"),
    }


def source_site(finding: dict, fallback: Path) -> str:
    source = Path(finding.get("file") or fallback).name
    line = finding.get("file_line", finding.get("line", 0))
    function = finding.get("function", finding.get("name", "?"))
    return f"{source}:{line} {function} {finding.get('kind', 'unknown')}"


def validate_report(report: object, returncode: int) -> str | None:
    if not isinstance(report, dict):
        return "invalid-report"
    summary = report.get("summary")
    replay = report.get("replay")
    details = report.get("declaration_details")
    findings = report.get("findings")
    if (not isinstance(summary, dict) or not isinstance(replay, dict)
            or not isinstance(details, list) or not isinstance(findings, list)):
        return "incomplete-report"
    status = report.get("status")
    expected_exit = {"proved": 0, "failed": 1}.get(status)
    if expected_exit is None:
        return f"unknown-status: {status!r}"
    if returncode != expected_exit:
        return f"status-exit-mismatch: status={status!r}, exit={returncode}"
    certificates = replay.get("certificates")
    replayed = replay.get("replayed")
    gaps = replay.get("gaps")
    if (type(certificates) is not int or type(replayed) is not int or type(gaps) is not int
            or certificates != replayed or gaps != 0):
        return "incomplete-replay"
    proven = summary.get("proven")
    obligations = summary.get("obligations")
    if (type(proven) is not int or type(obligations) is not int
            or proven < 0 or obligations < proven):
        return "invalid-summary"
    if status == "proved" and proven != obligations:
        return "proved-status-with-unproven-obligations"
    return None


def process_rss_kib(pid: int) -> int | None:
    try:
        output = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True,
                                text=True, check=False, timeout=1).stdout.strip()
        return int(output) if output else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def run(path: Path, timeout: int, rss_limit_kib: int) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.Popen([str(BINARY), "--json", str(path)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True)
    except OSError as error:
        return {"input": str(path), "input_sha256": sha256(path),
                "seconds": round(time.monotonic() - started, 3),
                "error": f"execution-error: {error}"}
    peak_rss_kib = 0
    stop_reason = None
    while proc.poll() is None:
        rss = process_rss_kib(proc.pid)
        if rss is not None:
            peak_rss_kib = max(peak_rss_kib, rss)
        if time.monotonic() - started >= timeout:
            stop_reason = "timeout"
        elif peak_rss_kib >= rss_limit_kib:
            stop_reason = "rss-limit"
        if stop_reason:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            break
        time.sleep(0.025)
    stdout, stderr = proc.communicate()
    elapsed = round(time.monotonic() - started, 3)
    common = {"input": str(path), "input_sha256": sha256(path), "seconds": elapsed,
              "peak_rss_kib": peak_rss_kib, "exit_code": proc.returncode}
    if stop_reason:
        return {**common, "error": stop_reason,
                "stderr": stderr[-2000:].decode("utf-8", errors="replace")}
    try:
        report = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {**common, "error": "invalid-json", "stdout_bytes": len(stdout),
                "stderr": stderr[-2000:].decode("utf-8", errors="replace")}
    validation_error = validate_report(report, proc.returncode)
    if validation_error:
        return {**common, "error": validation_error}

    details = report.get("declaration_details", [])
    findings = report.get("findings", [])
    unresolved = [
        {key: declaration.get(key) for key in
         ("kind", "name", "line", "verified", "verification_reason")}
        for declaration in details
        if isinstance(declaration, dict) and declaration.get("verified") is False
    ] if isinstance(details, list) else []
    unsupported_sites = sorted({
        source_site(finding, path)
        for finding in findings
        if isinstance(finding, dict) and finding.get("status") == "unsupported"
    }) if isinstance(findings, list) else []
    return {
        **common,
        "status": report.get("status"),
        "verification_state": report.get("verification_state"),
        "summary": report["summary"],
        "replay": report.get("replay"),
        "unverified_declarations": unresolved,
        "unsupported_sites": unsupported_sites,
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--rss-limit-kib", type=int, default=1_500_000)
    args = parser.parse_args()
    if args.timeout_seconds < 1 or args.rss_limit_kib < 1:
        parser.error("timeout and RSS limit must be positive")
    paths = [path.resolve() for path in args.inputs]
    if len(set(paths)) != len(paths):
        parser.error("duplicate input path")
    for path in paths:
        if not path.is_file():
            parser.error(f"input does not exist: {path}")
    before = identity()
    input_hashes_before = {str(path): sha256(path) for path in paths}
    results = [run(path, args.timeout_seconds, args.rss_limit_kib) for path in paths]
    input_hashes_after = {str(path): sha256(path) for path in paths}
    after = identity()
    if before != after:
        raise RuntimeError("binary or proof source identity changed during the P-07 run")
    if input_hashes_before != input_hashes_after:
        raise RuntimeError("an input changed during the P-07 run")

    affected = defaultdict(set)
    declaration_impact = defaultdict(set)
    for result in results:
        if result.get("error") is not None:
            continue
        for site in result.get("unsupported_sites", []):
            affected[site].add(result["input"])
        for declaration in result.get("unverified_declarations", []):
            key = (declaration.get("kind"), declaration.get("name"),
                   declaration.get("line"), declaration.get("verification_reason"))
            declaration_impact[key].add(result["input"])
    ranked_sites = [
        {"site": site, "affected_inputs": sorted(inputs), "input_count": len(inputs)}
        for site, inputs in sorted(affected.items(), key=lambda item: (-len(item[1]), item[0]))
    ]
    ranked_declarations = [
        {"kind": key[0], "name": key[1], "line": key[2], "root_cause": key[3],
         "affected_inputs": sorted(inputs), "input_count": len(inputs)}
        for key, inputs in sorted(declaration_impact.items(),
                                  key=lambda item: (-len(item[1]), str(item[0])))
    ]
    output = {
        "schema": "elisa-proof-p07-support-census-v1",
        "date": datetime.now(timezone.utc).date().isoformat(),
        "identity": before,
        "input_hashes": input_hashes_before,
        "timeout_seconds_per_input": args.timeout_seconds,
        "rss_limit_kib_per_process": args.rss_limit_kib,
        "inputs": results,
        "ranked_unverified_declarations": ranked_declarations,
        "ranked_unsupported_sites": ranked_sites,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    failed = sum(result.get("error") is not None for result in results)
    print(f"P-07 support census: {len(results)} inputs, {failed} incomplete reports, "
          f"{len(ranked_sites)} unsupported source sites")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
