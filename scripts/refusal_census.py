"""Refusal census (BACKLOG A-01): run every example, bucket each unproven goal by finding kind
and message, and write a deterministic JSON + Markdown table. Orchestration only."""
import json
import os
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs/census"


def run(path, timeout=120):
    started = time.monotonic()
    try:
        result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=timeout)
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return path.name, None
    data["_seconds"] = round(time.monotonic() - started, 2)
    return path.name, data


def main():
    files = sorted((ROOT / "examples").glob("*.elisa"))
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        results = list(pool.map(run, files))
    # A timeout under parallel load is not a refusal: retry serially, with a longer limit, the files
    # the committed census could read (the runtime harness examples never produce a report).
    baseline_path = ROOT / "docs/census/census.json"
    known = set(json.loads(baseline_path.read_text())["files"]) if baseline_path.exists() else set()
    results = [(name, data) if data is not None or name not in known else run(ROOT / "examples" / name, 600)
               for name, data in results]
    gates = Counter()
    per_file = {}
    proven = total = 0
    unreadable = []
    for name, data in results:
        if data is None:
            unreadable.append(name)
            continue
        summary = data.get("summary", {})
        proven += summary.get("proven", 0)
        total += summary.get("obligations", 0)
        file_gates = set()
        for finding in data.get("findings", []):
            gate = finding.get("refusal_gate") or f"{finding.get('kind')}: {finding.get('message')}"
            gates[gate] += 1
            file_gates.add(gate)
        per_file[name] = {"proven": summary.get("proven", 0), "obligations": summary.get("obligations", 0),
                          "gates": sorted(file_gates), "seconds": data["_seconds"]}
    report = {"examples": len(files), "proven": proven, "obligations": total,
              "unreadable": sorted(unreadable), "gates": dict(sorted(gates.items(), key=lambda kv: (-kv[1], kv[0]))),
              "files": per_file}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "census.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    lines = ["# Refusal census", "", f"{len(files)} examples, {proven}/{total} obligations proven.", "",
             "| Count | Gate |", "| ---: | --- |"]
    lines += [f"| {count} | {gate.replace('|', '/')} |" for gate, count in report["gates"].items()]
    slowest = sorted(per_file.items(), key=lambda item: -item[1]["seconds"])[:10]
    lines += ["", "## Slowest examples", "", "Wall time under the census's parallel load, so treat it as a ranking.",
              "", "| Seconds | Example |", "| ---: | --- |"]
    lines += [f"| {entry['seconds']:.2f} | {name} |" for name, entry in slowest]
    (OUT / "census.md").write_text("\n".join(lines) + "\n")
    print(f"census: {proven}/{total} proven across {len(files)} examples, {len(gates)} gates, {len(unreadable)} unreadable")


if __name__ == "__main__":
    main()
