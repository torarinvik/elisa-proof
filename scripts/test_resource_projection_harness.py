"""Resource report accounting controls; no proof process is launched."""
import ast
import copy
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

if not __debug__:
    raise SystemExit("run without Python -O")

source = Path(__file__).with_name("test_resource_projection_e144_coverage.py")
tree = ast.parse(source.read_text())
helper = ast.Module(body=[node for node in tree.body
                         if isinstance(node, ast.FunctionDef) and node.name == "report"],
                    type_ignores=[])
scope = {"json": json, "subprocess": subprocess, "ROOT": Path("unused"),
         "BINARY": Path("unused")}
exec(compile(helper, str(source), "exec"), scope)

valid = {"status": "proved",
         "summary": {"semantic_errors": 0, "obligations": 1, "proven": 1, "unproven": 0},
         "replay": {"certificates": 1, "replayed": 1, "gaps": 0}}

def run(payload, code=0):
    process = subprocess.CompletedProcess([], code, json.dumps(payload), "")
    with patch.object(subprocess, "run", return_value=process):
        return scope["report"]("control", 0, "proved")

def refuse(payload, code=0):
    try:
        run(payload, code)
    except (AssertionError, KeyError, TypeError):
        return
    raise AssertionError(("malformed report accepted", payload, code))

assert run(valid) == valid
for section in ("summary", "replay"):
    for field in valid[section]:
        for bad in (True, False, -1, "0", None):
            payload = copy.deepcopy(valid)
            payload[section][field] = bad
            refuse(payload)
        payload = copy.deepcopy(valid)
        del payload[section][field]
        refuse(payload)
for field, bad in (("gaps", 1), ("replayed", 0)):
    payload = copy.deepcopy(valid)
    payload["replay"][field] = bad
    refuse(payload)
refuse(valid, -11)
refuse({})
print("resource harness: malformed/missing counters, replay gaps, incomplete replay and crashes refuse")
