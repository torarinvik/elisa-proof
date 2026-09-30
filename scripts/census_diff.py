"""Census diff (BACKLOG A-03): rerun the refusal census into a scratch directory and fail when an
example proves fewer goals than the committed census or refuses with a gate it did not have before.
Orchestration only; improvements are reported so the committed census can be refreshed."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from refusal_census import run as run_census

RETRY_TIMEOUT_SECONDS = 600


def attach_measurements(census, path):
    """Attach optional wall times for comparisons without polluting stable census data."""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return
    for name, measurement in data.get("files", {}).items():
        if name in census["files"] and isinstance(measurement.get("seconds"), (float, int)):
            census["files"][name]["seconds"] = measurement["seconds"]


def retry_newly_unreadable(baseline, current, retry=run_census):
    """Retry only baseline-readable inputs lost to a transient census timeout."""
    retry_names = [name for name in current.get("unreadable", []) if name in baseline.get("files", {})]
    for name in retry_names:
        source = ROOT / name if name.startswith("src/") else ROOT / "examples" / name
        _, data, seconds, _ = retry(source, RETRY_TIMEOUT_SECONDS)
        if data is None:
            continue

        summary = data["summary"]
        gates = sorted({finding["refusal_gate"] for finding in data["findings"]
                        if finding.get("refusal_gate")})
        diagnostics = sorted({
            f"{finding.get('kind', 'unknown')}: {finding.get('message', '')}"
            for finding in data["findings"] if not finding.get("refusal_gate")
        })
        current["files"][name] = {
            "proven": summary["proven"],
            "obligations": summary["obligations"],
            "gates": gates,
            "diagnostics": diagnostics,
            "seconds": seconds,
        }
        current["unreadable"].remove(name)
        current.get("unreadable_reasons", {}).pop(name, None)
        current["proven"] += summary["proven"]
        current["obligations"] += summary["obligations"]


def main():
    # Optional arguments: BASELINE CURRENT census files, compared without rerunning (used by the tests).
    baseline = json.loads(Path(sys.argv[1] if len(sys.argv) > 2 else ROOT / "docs/census/census.json").read_text())
    if len(sys.argv) <= 2:
        # Accept the historical combined report while migrating to the stable report + timing sidecar.
        attach_measurements(baseline, ROOT / "docs/census/measurements.json")
    if len(sys.argv) > 2:
        current = json.loads(Path(sys.argv[2]).read_text())
    else:
        with tempfile.TemporaryDirectory() as scratch:
            subprocess.run([sys.executable, str(ROOT / "scripts/refusal_census.py"), scratch], check=True,
                           stdout=subprocess.DEVNULL)
            current = json.loads((Path(scratch) / "census.json").read_text())
            attach_measurements(current, Path(scratch) / "measurements.json")
            retry_newly_unreadable(baseline, current)
    regressions, gains = [], []
    for name, old in baseline["files"].items():
        new = current["files"].get(name)
        if new is None:
            if name in current["unreadable"]:
                regressions.append(f"{name}: no longer produces a readable report")
            else:
                regressions.append(f"{name}: source is absent from the current census")
            continue
        if new["proven"] < old["proven"]:
            regressions.append(f"{name}: proven {old['proven']} -> {new['proven']}")
        elif new["proven"] > old["proven"]:
            gains.append(f"{name}: proven {old['proven']} -> {new['proven']}")
        # Timing is noisy under parallel load: only a doubling on an example that already takes
        # seconds, beyond a fixed slack, counts as a replay blowup.
        if old.get("seconds", 0) >= 2 and new.get("seconds", 0) > 2 * old["seconds"] + 5:
            regressions.append(f"{name}: wall time {old['seconds']}s -> {new['seconds']}s")
        added = sorted(set(new.get("gates", [])) - set(old.get("gates", new.get("gates", []))))
        if added:
            regressions.append(f"{name}: new refusal gates {added}")
    for line in gains:
        print(f"census gain: {line}")
    if regressions:
        for line in regressions:
            print(f"census regression: {line}", file=sys.stderr)
        sys.exit(1)
    print(f"census diff: no regressions ({current['proven']}/{current['obligations']} proven; "
          f"baseline {baseline['proven']}/{baseline['obligations']})")


if __name__ == "__main__":
    main()
