"""Census diff (BACKLOG A-03): rerun the refusal census into a scratch directory and fail when an
example proves fewer goals than the committed census or refuses with a gate it did not have before.
Orchestration only; improvements are reported so the committed census can be refreshed."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def attach_measurements(census, path):
    """Attach optional wall times for comparisons without polluting stable census data."""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return
    for name, measurement in data.get("files", {}).items():
        if name in census["files"] and isinstance(measurement.get("seconds"), (float, int)):
            census["files"][name]["seconds"] = measurement["seconds"]


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


main()
