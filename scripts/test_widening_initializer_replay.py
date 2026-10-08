"""Match-payload widening facts replay without admitting stronger false bounds."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from portable_replay_support import BINARY, REPLAY, TRUST

if not __debug__:
    raise SystemExit("run without Python -O")

source = (ROOT / "examples/widening_cast.elisa").read_text()
start = source.index("def wide_first(")
end = source.index("\ndef param_after_call(", start)
body = source[start:end]
assert body.count("ensure result >= 0") == 1
assert body.count("wide: i64 = value.i64()") == 1

with tempfile.TemporaryDirectory(prefix="widening-initializer-replay-") as directory:
    work = Path(directory)
    for label, replacement, expected in (
        ("exact", body, 0),
        ("stronger_bound", body.replace("ensure result >= 0", "ensure result >= 1"), 1),
        ("changed_initializer", body.replace("wide: i64 = value.i64()",
                                            "wide: i64 = value.i64() - 1"), 1),
    ):
        path = work / (label + ".elisa")
        path.write_text(source[:start] + replacement + source[end:])
        for route in (("--json",), ("--function-json", "wide_first")):
            run = subprocess.run([str(BINARY), *route, str(path)],
                                 capture_output=True, text=True, timeout=60)
            report = json.loads(run.stdout)
            info = {k: report[k] for k in ("status", "summary", "replay", "findings")}
            assert run.returncode == expected, (label, route, run.returncode, info)
            assert report["summary"]["semantic_errors"] == 0, info
            assert report["replay"]["gaps"] == 0, info
            assert report["replay"]["certificates"] == report["replay"]["replayed"], info
            if expected:
                assert any(f["name"] == "wide_first" and f["kind"] == "ensure-unproven"
                           for f in report["findings"]), info
                assert not any(d.get("name") == "wide_first" and d.get("verified")
                               for d in report["declaration_details"]), info
            else:
                assert report["status"] == "proved", info
        if expected == 0:
            exported = subprocess.run([str(BINARY), "--package", str(path)],
                                      capture_output=True, text=True, timeout=60)
            assert exported.returncode == 0, exported.stderr
            package = work / "exact.json"
            package.write_text(exported.stdout)
            fresh = subprocess.run([str(REPLAY), str(package)], capture_output=True,
                                   text=True, timeout=60)
            replay = json.loads(fresh.stdout)
            assert fresh.returncode == 0 and replay["status"] == "replayed", replay
            assert replay["trust"] == TRUST, replay

print("match-payload widening replays; stronger/changed claims reject; fresh package replay passes")
