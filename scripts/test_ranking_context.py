"""Ranking premise filtering retains pinned names and checked type evidence."""
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("ranking checks must run without Python -O")
ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))

for fixture, count in (("lexicographic_decreases", 38),
                       ("lexicographic_recursive_lemma", 14),
                       ("recursive_lemma_decreases", 9)):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / (fixture + ".elisa"))],
                         capture_output=True, text=True, timeout=60)
    report = json.loads(run.stdout)
    assert run.returncode == 0 and report["status"] == "proved", fixture
    assert report["summary"]["obligations"] == count, (fixture, report["summary"])
    assert report["summary"]["proven"] == count and not report["findings"], fixture
    assert report["summary"]["semantic_errors"] == 0, fixture
    assert report["replay"] == {"certificates": count, "replayed": count, "gaps": 0}, fixture

for fixture in ("rejected_lexicographic_decreases", "rejected_recursive_lemma_decreases"):
    run = subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / (fixture + ".elisa"))],
                         capture_output=True, text=True, timeout=60)
    report = json.loads(run.stdout)
    assert run.returncode == 1 and report["status"] == "failed", fixture
    assert report["summary"]["unproven"] > 0 and report["findings"], fixture
    assert not any(row["proved"] for row in report["functions"]), fixture
    assert all(not goal["proven"] or goal["replay_status"] == "replayed"
               for goal in report["goals"]), fixture
print("ranking context: pinned components replay; invalid recursive contracts remain unproved")
