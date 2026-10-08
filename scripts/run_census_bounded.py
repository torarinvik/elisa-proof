#!/usr/bin/env python3
"""Run the complete refusal census with aggregate RSS and per-process evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def sample_processes(root_pid):
    rows = subprocess.check_output(
        ["ps", "-axo", "pid=,ppid=,pgid=,rss="], text=True
    )
    processes = [tuple(map(int, row.split())) for row in rows.splitlines() if row.strip()]
    owned = {root_pid}
    while True:
        descendants = {pid for pid, parent, group, _ in processes
                       if parent in owned or group == root_pid}
        expanded = owned | descendants
        if expanded == owned:
            break
        owned = expanded
    return [{"pid": pid, "parent_pid": parent, "rss_kb": rss}
            for pid, parent, _, rss in processes if pid in owned]


def stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--rss-kb", type=int, default=8388608)
    parser.add_argument("--seconds", type=int, default=1800)
    parser.add_argument("--input-seconds", type=int, default=120)
    args = parser.parse_args()
    if min(args.workers, args.rss_kb, args.seconds, args.input_seconds) < 1:
        parser.error("workers, RSS and time limits must be positive")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).with_name("refusal_census.py")
    command = [sys.executable, str(script), str(output), "--workers", str(args.workers),
               "--timeout-seconds", str(args.input_seconds)]
    census_sha256 = hashlib.sha256(script.read_bytes()).hexdigest()
    runner_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    started = time.monotonic()
    peak = 0
    peak_processes = []
    by_pid = {}
    reason = "completed"
    with (output / "execution.log").open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            while process.poll() is None:
                sample = sample_processes(process.pid)
                rss = sum(row["rss_kb"] for row in sample)
                if rss > peak:
                    peak, peak_processes = rss, sample
                elapsed = time.monotonic() - started
                for row in sample:
                    previous = by_pid.get(row["pid"])
                    if previous is None:
                        # Inspect only owned processes; retain the source input command,
                        # never the environment or unrelated system process arguments.
                        try:
                            command_text = subprocess.check_output(
                                ["ps", "-p", str(row["pid"]), "-o", "command="], text=True
                            ).strip()
                        except subprocess.CalledProcessError:
                            command_text = ""
                        by_pid[row["pid"]] = dict(row, command=command_text,
                                                 first_seen_seconds=round(elapsed, 2))
                    elif row["rss_kb"] > previous["rss_kb"]:
                        previous["rss_kb"] = row["rss_kb"]
                if rss > args.rss_kb or elapsed > args.seconds:
                    reason = "rss" if rss > args.rss_kb else "timeout"
                    stop(process)
                    break
                time.sleep(0.25)
        except BaseException:
            reason = "interrupted"
            raise
        finally:
            if process.poll() is None:
                stop(process)
            evidence = {
                "command": command, "status": process.returncode, "reason": reason,
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "limit_rss_kb": args.rss_kb, "limit_seconds": args.seconds,
                "peak_rss_kb": peak, "processes_at_peak": peak_processes,
                "process_peaks": list(by_pid.values()),
                "census_script_sha256": census_sha256,
                "runner_sha256": runner_sha256,
                "scripts_unchanged": (
                    census_sha256 == hashlib.sha256(script.read_bytes()).hexdigest()
                    and runner_sha256 == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
                ),
            }
            (output / "execution.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({key: evidence[key] for key in
                      ("status", "reason", "elapsed_seconds", "peak_rss_kb")}))
    return process.returncode if reason == "completed" and process.returncode >= 0 else 125


if __name__ == "__main__":
    raise SystemExit(main())
