"""Adversarial whole-kernel report accounting, without launching proof search."""
import copy
import io
import json
from pathlib import Path
import runpy
from unittest.mock import patch

if not __debug__:
    raise SystemExit("run without Python -O")

validator = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                               "test/validate_kernel_replay_standalone.py"))
valid = {
    "status": "failed", "verification_state": "unsupported",
    "summary": {"semantic_errors": 0, "obligations": 271, "proven": 270, "unproven": 1},
    "replay": {"certificates": 270, "replayed": 270, "gaps": 0},
    "declaration_details": [{"kind": "function", "name": name, "verified": True}
                            for name in validator["REQUIRED_VERIFIED_DECLARATIONS"]],
    "findings": [], "trust": {"trusted_assumptions": []},
    "measurements": {"kernel_nodes": 1, "kernel_nodes_shared": 3},
    "kernel": {"nodes": [{}]},
}

def run(payload):
    with patch("sys.stdin", io.StringIO(json.dumps(payload))):
        validator["main"]()

def refuse(payload):
    try:
        run(payload)
    except (AssertionError, KeyError, TypeError):
        return
    raise AssertionError("malformed kernel audit was accepted")

run(valid)
for section in ("summary", "replay"):
    for field in valid[section]:
        for bad in (True, False, -1, "0", None):
            payload = copy.deepcopy(valid)
            payload[section][field] = bad
            refuse(payload)
payload = copy.deepcopy(valid)
payload["replay"].update(certificates=0, replayed=0)
refuse(payload)
payload = copy.deepcopy(valid)
payload["summary"]["obligations"] += 1
refuse(payload)
payload = copy.deepcopy(valid)
payload["declaration_details"].pop()
refuse(payload)
print("kernel audit: malformed counters, missing certificates, incomplete accounting and lost coverage refuse")
