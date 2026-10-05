"""Persisted packages are replayed afresh; disk metadata is never an admission proof."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PRODUCER = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
REPLAY = Path(os.environ.get("ELISA_PROOF_REPLAY_BIN", ROOT / "build/elisa-proof-replay"))


def run_replay(package_path):
    # This invocation starts a new process with no producer-side report/search state.
    result = subprocess.run([str(REPLAY), str(package_path)], capture_output=True, text=True, timeout=60)
    return result.returncode, json.loads(result.stdout)


with tempfile.TemporaryDirectory(prefix="elisa-p05-restart-") as directory:
    work = Path(directory)
    source = ROOT / "examples" / "verified.elisa"
    produced = subprocess.run([str(PRODUCER), "--package", str(source)],
                              capture_output=True, text=True, timeout=60)
    assert produced.returncode == 0, (produced.returncode, produced.stderr)
    package = json.loads(produced.stdout)
    assert package["theorems"], "positive fixture must contain a persisted certificate"
    assert package["source"]["authenticated"] is False

    persisted = work / "valid.json"
    persisted.write_text(json.dumps(package), encoding="utf-8")
    code, result = run_replay(persisted)
    assert code == 0 and result["status"] == "replayed", result
    assert result["summary"]["replayed"] == len(package["theorems"]), result

    # A stale/inadmissible source marker cannot be made valid by retaining serialized theorems.
    stale = copy.deepcopy(package)
    stale["source"]["admissible"] = False
    stale_path = work / "stale.json"
    stale_path.write_text(json.dumps(stale), encoding="utf-8")
    code, result = run_replay(stale_path)
    assert code == 1 and result["status"] == "rejected" and result["reason"] == "source-inadmissible", result

    # A disk-provided success bit is outside the admitted theorem schema, even when true.
    forged = copy.deepcopy(package)
    forged["theorems"][0]["proven"] = True
    forged_path = work / "forged.json"
    forged_path.write_text(json.dumps(forged), encoding="utf-8")
    code, result = run_replay(forged_path)
    assert code == 1 and result["status"] == "malformed" and result["reason"] == "theorem-schema", result

    truncated_path = work / "truncated.json"
    truncated_path.write_text(persisted.read_text(encoding="utf-8")[:-1], encoding="utf-8")
    code, result = run_replay(truncated_path)
    assert code == 1 and result["status"] == "malformed" and result["reason"] == "json", result

print("P-05 package restart: persisted certificate replayed in a fresh process; stale, forged and truncated artifacts refused")
