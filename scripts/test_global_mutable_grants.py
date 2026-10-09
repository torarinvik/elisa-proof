"""Mutable global accesses must carry the corresponding Global grants."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
if not __debug__:
    raise SystemExit("run without Python -O: assertions must remain enabled")

def context(route, name, report):
    fields = ("status", "summary", "semantic_diagnostics", "findings", "replay")
    return {"route": route, "case": name,
            **{field: report.get(field) for field in fields}}

def run(fixture, target, route):
    # Isolate each case: one missing grant must not mask a different accepted case.
    chunks = (ROOT / "examples" / fixture).read_text().split("\ndef ")
    selected = [chunk for chunk in chunks[1:] if chunk.startswith(target + "(")]
    assert len(selected) == 1, target
    if target in ("forward_read", "forward_missing_read"):
        helper = [chunk for chunk in chunks[1:] if chunk.startswith("read_counter(")]
        assert len(helper) == 1
        selected.insert(0, helper[0])
    with tempfile.TemporaryDirectory(prefix="proof-global-grants-") as directory:
        source = Path(directory) / "case.elisa"
        source.write_text(chunks[0] + "\ndef " + "\ndef ".join(selected))
        process = subprocess.run(([BIN, "--function-json", target, str(source)] if route == "function"
                                  else [BIN, "--json", str(source)]),
                                 capture_output=True, text=True, timeout=60)
    report = json.loads(process.stdout)
    assert report["replay"]["gaps"] == 0, context(route, target, report)
    return process.returncode, report

for route in ("function", "module"):
    for name in ("read_counter", "write_counter", "copy_counter", "shadow_counter",
                 "local_shadow", "block_shadow_then_global", "forward_read", "inferred_read",
                 "indexed_read", "indexed_write", "mutable_reference_acquisition"):
        code, report = run("global_mutable_grants.elisa", name, route)
        assert code == 0 and report["status"] == "proved", context(route, name, report)
        assert report["summary"]["semantic_errors"] == 0, context(route, name, report)

    for name in ("missing_read", "missing_write", "write_only_reads",
                 "read_only_writes", "read_only_update",
                 "read_before_local_shadow", "read_after_block_shadow", "forward_missing_read",
                 "signature_only_read", "signature_only_write", "indexed_read_write_only",
                 "indexed_write_read_only", "mutable_reference_read_only",
                 "mutable_reference_write_only"):
        code, report = run("rejected_global_mutable_grants.elisa", name, route)
        assert code != 0 and report["status"] != "proved", context(route, name, report)
        assert report["summary"]["semantic_errors"] > 0, context(route, name, report)
        assert not any(d.get("name") == name and d.get("verified")
                       for d in report["declaration_details"]), context(route, name, report)
        required = {
            "indexed_read_write_only": ("Global.Read", "permission_values"),
            "indexed_write_read_only": ("Global.Write", "permission_values"),
            "mutable_reference_read_only": ("Global.Write", "permission_counter"),
            "mutable_reference_write_only": ("Global.Read", "permission_counter"),
        }.get(name)
        if required is not None:
            effect, global_name = required
            assert any(d.get("severity") == 1 and d.get("expected") == effect
                       and d.get("actual") == global_name
                       for d in report["semantic_diagnostics"]), context(route, name, report)

print("Global grants cover reads/writes separately; both report routes reject missing/wrong grants")
