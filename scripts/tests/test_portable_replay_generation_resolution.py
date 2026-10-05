"""Portable replay selects both products from one published generation."""
import ast
import json
import os
from pathlib import Path
import runpy
import subprocess
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SUPPORT = ROOT / "scripts/portable_replay_support.py"
PAIRED_CONSUMER = ROOT / "scripts/test_p05_package_restart.py"
PAIR = {
    "products": {
        "elisa-proof": {"binary": "/generation-a/elisa-proof"},
        "elisa-proof-replay": {"binary": "/generation-a/elisa-proof-replay"},
    }
}

with mock.patch.dict(os.environ, {"ELISA_PROOF_BIN": "", "ELISA_PROOF_REPLAY_BIN": "",
                                  "ELISA_PROOF_GENERATION_ROOT": "/tmp/mock-generations"}), \
     mock.patch.object(subprocess, "run", return_value=mock.Mock(stdout=json.dumps(PAIR))) as run:
    support = runpy.run_path(str(SUPPORT))
    assert support["BINARY"] == Path("/generation-a/elisa-proof")
    assert support["REPLAY"] == Path("/generation-a/elisa-proof-replay")
    assert run.call_count == 1, run.call_args_list
    command = run.call_args.args[0]
    assert command[command.index("resolve") + 1:] == ["--generation-root", "/tmp/mock-generations"]

with mock.patch.dict(os.environ, {"ELISA_PROOF_BIN": "/custom/proof",
                                  "ELISA_PROOF_REPLAY_BIN": "/custom/replay"}), \
     mock.patch.object(subprocess, "run", side_effect=AssertionError("resolver should be bypassed")):
    support = runpy.run_path(str(SUPPORT))
    assert support["BINARY"] == Path("/custom/proof")
    assert support["REPLAY"] == Path("/custom/replay")

try:
    with mock.patch.dict(os.environ, {"ELISA_PROOF_BIN": "/custom/proof",
                                      "ELISA_PROOF_REPLAY_BIN": ""}):
        runpy.run_path(str(SUPPORT))
except RuntimeError as error:
    assert "both ELISA_PROOF_BIN and ELISA_PROOF_REPLAY_BIN" in str(error)
else:
    raise AssertionError("a partial product override must be rejected")

print("portable replay product selection: one generation resolve; paired overrides retained")

# The restart consumer launches both roles, so it must take them from the same
# resolver instead of independently selecting environment defaults.
consumer_tree = ast.parse(PAIRED_CONSUMER.read_text(encoding="utf-8"))
imports_pair = any(
    isinstance(node, ast.ImportFrom) and node.module == "portable_replay_support"
    and {(alias.name, alias.asname) for alias in node.names}
    >= {("BINARY", "PRODUCER"), ("REPLAY", None)}
    for node in ast.walk(consumer_tree)
)
assert imports_pair, "package restart must use the shared paired product resolver"
assert not any(
    isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    and node.value.id == "os" and node.attr == "environ"
    for node in ast.walk(consumer_tree)
), "package restart must not independently read product overrides"

print("portable package restart: producer and replay are pinned through the shared resolver")
