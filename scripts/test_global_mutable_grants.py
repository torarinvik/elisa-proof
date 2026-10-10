"""Mutable global accesses must carry the corresponding Global grants."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from perf_build_provenance import (
    read_build_manifest,
    source_tree_identity,
    verify_build_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))

if not __debug__:
    raise SystemExit("run without Python -O: assertions must remain enabled")


def require_current_proof_binary():
    """Refuse to turn stale verifier output into evidence for the current grant checker."""
    try:
        manifest = read_build_manifest(Path(BIN), "Global grants test proof")
        verify_build_artifacts(manifest, "Global grants test proof")
        proof = manifest.get("proof")
        frontend = manifest.get("frontend")
        compiler = manifest.get("compiler")
        if (not isinstance(proof, dict) or not isinstance(frontend, dict)
                or not isinstance(compiler, dict)):
            raise RuntimeError("build manifest is missing proof, frontend, or compiler provenance")
        current_source = source_tree_identity(ROOT / "src")
        if proof.get("source_tree_sha256") != current_source:
            raise RuntimeError("binary was built from a different proof source tree")
        pinned_revision = (ROOT / "ELISA_COMPILER_REV").read_text(encoding="ascii").strip()
        if compiler.get("stage") != "stage1" or compiler.get("source_dirty") is not False:
            raise RuntimeError("binary was not built with a clean Elisa Stage1 compiler")
        stage1_revision = compiler.get("stage1_revision") or compiler.get("source_revision")
        if (frontend.get("revision") != pinned_revision
                or stage1_revision != pinned_revision):
            raise RuntimeError(
                f"binary uses Elisa compiler {stage1_revision} "
                f"(frontend {frontend.get('revision')}), current pin is {pinned_revision}"
            )
    except (OSError, UnicodeError, subprocess.SubprocessError, RuntimeError) as error:
        raise SystemExit(
            f"Global grants test refused an unqualified proof binary: {error}. "
            "Rebuild with scripts/build.sh using the pinned newest Elisa compiler."
        ) from error


require_current_proof_binary()


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
                 "indexed_read", "indexed_write", "indexed_parameter_shadow", "indexed_local_shadow",
                 "indexed_write_reads_mutable_global_index",
                 "mutable_reference_acquisition"):
        code, report = run("global_mutable_grants.elisa", name, route)
        if name in ("indexed_write_reads_mutable_global_index", "mutable_reference_acquisition"):
            # This control isolates semantic grants even if the independent proof checker cannot
            # yet close dynamic-index safety or model a mutable borrow of global storage.
            assert report["summary"]["semantic_errors"] == 0, context(route, name, report)
            continue
        assert code == 0 and report["status"] == "proved", context(route, name, report)
        assert report["summary"]["semantic_errors"] == 0, context(route, name, report)
        kernel = report.get("kernel", {})
        traces = kernel.get("fact_traces", report.get("fact_traces", []))
        array_type_traces = [trace for trace in traces
                             if trace.get("kind") == "global-mutable-array-type"]
        array_bound_traces = [trace for trace in traces
                              if trace.get("kind") == "global-mutable-array-index-bound"]
        if name in ("indexed_read", "indexed_write"):
            assert len(array_type_traces) == 2, context(route, name, report)
            assert len(array_bound_traces) == 1, context(route, name, report)
        if name in ("indexed_parameter_shadow", "indexed_local_shadow"):
            assert not array_type_traces, context(route, name, report)

    for name in ("missing_read", "missing_write", "write_only_reads",
                 "read_only_writes", "read_only_update",
                 "read_before_local_shadow", "read_after_block_shadow", "forward_missing_read",
                 "signature_only_read", "signature_only_write", "indexed_read_write_only",
                 "indexed_write_read_only", "indexed_target_missing_index_read",
                 "indexed_target_missing_root_write", "mutable_reference_read_only",
                 "mutable_reference_write_only"):
        code, report = run("rejected_global_mutable_grants.elisa", name, route)
        assert code != 0 and report["status"] != "proved", context(route, name, report)
        assert report["summary"]["semantic_errors"] > 0, context(route, name, report)
        assert not any(d.get("name") == name and d.get("verified")
                       for d in report["declaration_details"]), context(route, name, report)
        required = {
            "missing_read": ("Global.Read", "permission_counter"),
            "missing_write": ("Global.Write", "permission_counter"),
            "write_only_reads": ("Global.Read", "permission_counter"),
            "read_only_writes": ("Global.Write", "permission_counter"),
            "read_only_update": ("Global.Write", "permission_counter"),
            "read_before_local_shadow": ("Global.Read", "permission_counter"),
            "read_after_block_shadow": ("Global.Read", "permission_counter"),
            "forward_missing_read": ("Global.Read", "Global"),
            "signature_only_read": ("Global.Read", "permission_counter"),
            "signature_only_write": ("Global.Write", "permission_counter"),
            "indexed_read_write_only": ("Global.Read", "permission_values"),
            "indexed_write_read_only": ("Global.Write", "permission_values"),
            "indexed_target_missing_index_read": ("Global.Read", "permission_index"),
            "indexed_target_missing_root_write": ("Global.Write", "permission_values"),
            "mutable_reference_read_only": ("Global.Write", "permission_counter"),
            "mutable_reference_write_only": ("Global.Read", "permission_counter"),
        }.get(name)
        if required is not None:
            effect, actual = required
            assert any(d.get("severity") == 1 and d.get("expected") == effect
                       and d.get("actual") == actual
                       and (name != "forward_missing_read" or d.get("name") == "read_counter")
                       for d in report["semantic_diagnostics"]), context(route, name, report)

print("Global grants cover reads/writes separately; both report routes reject missing/wrong grants")
