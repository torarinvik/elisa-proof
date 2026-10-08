"""A copied element keeps its bound, while its mutable source equality expires."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof")).resolve()
SOURCE = """def copied(xs: mutable darray[i64]&, n: usize, p: i64, i: usize, j: usize) -> i64:
    requires n <= xs.count
    requires i < j
    requires j < n
    requires forall t in i..<j: p <= xs[t]
    ensures p <= result
    a: i64 = xs[i]
    xs[i] <- 0
    return a
"""

CASES = [
    ("copy_bound", SOURCE, True),
    ("missing_lower_point", SOURCE.replace("t in i..<j", "t in (i + 1)..<j"), False),
    ("upper_point", SOURCE.replace("a: i64 = xs[i]", "a: i64 = xs[j]"), False),
    ("changed_before_copy", SOURCE.replace("    a: i64 = xs[i]", "    xs[i] <- p - 1\n    a: i64 = xs[i]"), False),
    ("rebound_copy", SOURCE.replace("a: i64", "a: mutable i64").replace("    return a", "    a <- p - 1\n    return a"), False),
    ("changed_cell_equality", SOURCE.replace("ensures p <= result", "ensures result == xs[i]"), False),
    ("wrong_receiver", SOURCE.replace("n: usize", "ys: darray[i64]&, n: usize")
     .replace("    requires n <= xs.count", "    requires n <= xs.count\n    requires n <= ys.count")
     .replace("a: i64 = xs[i]", "a: i64 = ys[i]"), False),
]


def main():
    failures = []
    with tempfile.TemporaryDirectory(prefix="index-copy-bounds-") as directory:
        for name, source, accepted in CASES:
            path = Path(directory) / (name + ".elisa")
            path.write_text(source)
            result = subprocess.run([str(BINARY), "--json", str(path)],
                                    capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            complete = result.returncode == 0 and report["status"] == "proved"
            if accepted:
                summary, replay = report["summary"], report["replay"]
                complete = complete and summary["obligations"] == summary["proven"] == replay["certificates"] == replay["replayed"]
                complete = complete and replay["gaps"] == 0 and report["kernel"]["independent_replay"]
                complete = complete and not report["trust"]["trusted_assumptions"]
            if complete != accepted:
                failures.append(name)
            print(name, "accepted" if complete else "refused", report["replay"], flush=True)
    if failures:
        raise SystemExit("index-copy controls failed: " + ", ".join(failures))


if __name__ == "__main__":
    main()
