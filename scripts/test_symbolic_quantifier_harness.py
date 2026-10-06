"""Exercise report accounting without launching proof search."""
import ast
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

if not __debug__:
    raise SystemExit("run without Python -O")

source = Path(__file__).with_name("test_symbolic_quantifiers.py")
tree = ast.parse(source.read_text())
helpers = ast.Module(body=[node for node in tree.body
                          if isinstance(node, ast.FunctionDef)
                          and node.name in {"check", "report"}], type_ignores=[])
scope = {"json": json, "subprocess": subprocess, "BINARY": Path("unused"),
         "failures": []}
exec(compile(helpers, str(source), "exec"), scope)

def run(payload, code=0):
    scope["failures"].clear()
    process = subprocess.CompletedProcess([], code, json.dumps(payload), "")
    with patch.object(subprocess, "run", return_value=process):
        result = scope["report"](Path("control.elisa"))
    assert result == payload
    return list(scope["failures"])

valid = {"replay": {"certificates": 2, "replayed": 2, "gaps": 0}}
assert run(valid) == []
assert run(valid, 1) == []  # Refused source claims can still replay cleanly.
assert any("replay gaps" in f for f in run(
    {"replay": {"certificates": 2, "replayed": 2, "gaps": 1}}))
assert any("unreplayed certificates" in f for f in run(
    {"replay": {"certificates": 2, "replayed": 1, "gaps": 0}}))
assert any("no replay accounting" in f for f in run({}))
assert any("malformed replay accounting" in f for f in run({"replay": {}}))
assert any("malformed replay accounting" in f for f in run(
    {"replay": {"certificates": True, "replayed": True, "gaps": False}}))
assert any("signal" in f for f in run(valid, -11))
print("quantifier harness: replay gaps, missing accounting, unreplayed certificates and signals refuse")
