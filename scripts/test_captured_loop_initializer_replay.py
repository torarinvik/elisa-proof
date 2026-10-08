"""Captured loop initializer claims remain source-bound through fresh package replay."""
import json
from pathlib import Path
import subprocess
import tempfile
from portable_replay_support import BINARY, REPLAY, TRUST

ROOT = Path(__file__).resolve().parents[1]
source = """module M:
    const N: usize = 9
    def f() -> usize:
        result: usize =
            for i in 0..<N |count: usize = 0| -> count:
                invariant count <= N
                count <- count
        result
"""
if not __debug__:
    raise SystemExit("run without Python -O")

with tempfile.TemporaryDirectory(prefix="captured-initializer-replay-") as directory:
    work = Path(directory)
    cases = (
        ("genuine", source, True),
        ("false_initializer", source.replace("count: usize = 0", "count: usize = 10"), False),
        ("false_invariant", source.replace("count <= N", "count > N"), False),
        ("shadowed_constant", source.replace("def f()", "def f(N: usize)").replace(
            "count: usize = 0", "count: usize = 1"), False),
        ("stale_update", source.replace("count <- count", "count <- N + 1"), False),
    )
    for name, text, accepted in cases:
        path = work / (name + ".elisa")
        path.write_text(text)
        for route in (("--json",), ("--function-json", "f")):
            result = subprocess.run([str(BINARY), *route, str(path)], capture_output=True,
                                    text=True, timeout=60)
            report = json.loads(result.stdout)
            evidence = {key: report.get(key) for key in ("status", "summary", "replay", "findings")}
            assert result.returncode == (0 if accepted else 1), (name, route, evidence)
            assert report["replay"]["gaps"] == 0, (name, route, evidence)
            assert report["replay"]["certificates"] == report["replay"]["replayed"], evidence
            if accepted:
                assert report["status"] == "proved" and report["findings"] == [], evidence
            else:
                assert report["status"] != "proved", evidence
                assert not any(declaration.get("name") == "f" and declaration.get("verified")
                               for declaration in report["declaration_details"]), evidence
        if accepted:
            exported = subprocess.run([str(BINARY), "--package", str(path)],
                                      capture_output=True, text=True, timeout=60)
            assert exported.returncode == 0, exported.stderr
            package = work / "genuine.json"
            package.write_text(exported.stdout)
            checked = subprocess.run([str(REPLAY), str(package)], capture_output=True,
                                     text=True, timeout=60)
            report = json.loads(checked.stdout)
            assert checked.returncode == 0 and report["status"] == "replayed", report
            assert report["trust"] == TRUST, report

print("Captured initializer: genuine package replays; initializer/invariant/update/shadow mutations reject")
