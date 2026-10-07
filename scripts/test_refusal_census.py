"""Stable census summaries include every failed finding and exclude noisy timings."""
import json
import os
from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
from unittest.mock import patch

if not __debug__:
    raise SystemExit("refusal census checks must run without Python -O")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import refusal_census


def result(proven, obligations, findings, seconds, error=None):
    report = None if error else {
        "summary": {"proven": proven, "obligations": obligations},
        "findings": findings,
    }
    return {"report": report, "seconds": seconds, "error": error}


toolchain = {"compiler_stage": "stage1", "compiler_revision": "abc123"}
sample = {
    "examples/example.elisa": result(
        2,
        3,
        [
            {"refusal_gate": "no-rule", "kind": "ensure-unproven"},
            {"kind": "unsupported", "message": "no imported effect row"},
        ],
        4.25,
    ),
    "src/proof/kernel_core.elisa": result(4, 4, [], 1.5),
    "unreadable.elisa": result(0, 0, [], 12.0, "timeout"),
}

first = refusal_census.summarize(sample, 1, 1, "2026-09-30", toolchain)
different_timings = {
    name: {**entry, "seconds": entry["seconds"] * 3}
    for name, entry in sample.items()
}
second = refusal_census.summarize(different_timings, 1, 1, "2026-09-30", toolchain)
assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
assert first["proven"] == 6 and first["obligations"] == 7
assert first["unreadable"] == ["unreadable.elisa"]
assert first["unreadable_reasons"] == {"unreadable.elisa": "timeout"}
assert first["gates"] == {"no-rule": 1}
assert first["diagnostics"] == {"unsupported: no imported effect row": 1}
assert "seconds" not in first["files"]["examples/example.elisa"]
assert first["files"]["examples/example.elisa"]["gates"] == ["no-rule"]
assert first["files"]["examples/example.elisa"]["diagnostics"] == [
    "unsupported: no imported effect row"
]
assert "seconds" in refusal_census.measurements(sample, "2026-09-30", toolchain)["files"]["examples/example.elisa"]
summary_markdown = refusal_census.render_markdown(first)
assert "Wall time" not in summary_markdown
assert "First refusal gate" in summary_markdown
assert "Non-goal diagnostics" in summary_markdown
assert "timings" in refusal_census.render_measurements_markdown(
    refusal_census.measurements(sample, "2026-09-30", toolchain)
).lower()


def provenance_guard_test():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "src/proof.elisa"
        source.parent.mkdir()
        source.write_text("def proof() -> bool: return true\n")
        (root / "ELISA_COMPILER_REV").write_text("rev123\n")
        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Census Test"], check=True)
        subprocess.run(["git", "-C", str(root), "add", "ELISA_COMPILER_REV", "src/proof.elisa"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True)
        binary = root / "proof"
        binary.write_bytes(b"binary image")
        manifest = {
            "binary": {"sha256": hashlib.sha256(binary.read_bytes()).hexdigest()},
            "compiler": {"stage": "stage1", "source_revision": "rev123abc", "product": {"sha256": "product"}},
            "frontend": {"revision": "rev123"},
            "proof": {
                "head": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
                "source_tree_sha256": refusal_census.tree_sha256(root / "src"),
                "source_dirty": False,
            },
        }
        Path(str(binary) + ".manifest.json").write_text(json.dumps(manifest))
        old_root, old_binary = refusal_census.ROOT, refusal_census.BINARY
        refusal_census.ROOT, refusal_census.BINARY = root, binary
        saved_revision = os.environ.pop("ELISA_COMPILER_REV", None)
        try:
            with patch.dict(os.environ, {"ELISA_COMPILER_REV": ""}):
                assert refusal_census.toolchain_identity()["compiler_revision"] == "rev123abc"
            with patch.dict(os.environ, {"ELISA_COMPILER_REV": "rev123"}):
                assert refusal_census.toolchain_identity()["frontend_revision"] == "rev123"
            with patch.dict(os.environ, {"ELISA_COMPILER_REV": "wrong-revision"}):
                try:
                    refusal_census.toolchain_identity()
                except RuntimeError as error:
                    assert "provenance does not match" in str(error)
                else:
                    raise AssertionError("mismatched explicit compiler revision was accepted")
            source.write_text(source.read_text() + "# changed after build\n")
            try:
                refusal_census.toolchain_identity()
            except RuntimeError as error:
                assert "source tree changed" in str(error)
            else:
                raise AssertionError("stale proof source digest was accepted")
            source.write_text("def proof() -> bool: return true\n")
            binary.write_bytes(b"changed product")
            try:
                refusal_census.toolchain_identity()
            except RuntimeError as error:
                assert "SHA-256" in str(error)
            else:
                raise AssertionError("binary/manifest mismatch was accepted")
        finally:
            if saved_revision is not None:
                os.environ["ELISA_COMPILER_REV"] = saved_revision
            refusal_census.ROOT, refusal_census.BINARY = old_root, old_binary


def subprocess_result_lattice_test():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        binary = root / "fake-proof"
        source = ROOT / "examples/verified.elisa"
        old_binary = refusal_census.BINARY
        try:
            def run_stub(report, exit_code):
                payload = json.dumps(report)
                binary.write_text(
                    "#!/usr/bin/env python3\nimport sys\n"
                    f"print({payload!r})\nsys.exit({exit_code})\n",
                    encoding="utf-8",
                )
                binary.chmod(0o755)
                refusal_census.BINARY = binary
                return refusal_census.run(source, 10)

            proved = {
                "status": "proved", "verification_state": "proved",
                "summary": {"proven": 1, "obligations": 1}, "replay": {"gaps": 0}, "findings": [],
            }
            key, data, _, error = run_stub(proved, 1)
            assert key == "verified.elisa" and data is None and error == "exit-status-mismatch"
            key, data, _, error = run_stub(proved, 0)
            assert data == proved and error is None

            failed = {
                "status": "failed", "verification_state": "unknown",
                "summary": {"proven": 0, "obligations": 1}, "findings": [],
            }
            key, data, _, error = run_stub(failed, 0)
            assert key == "verified.elisa" and data is None and error == "exit-status-mismatch"
            key, data, _, error = run_stub(failed, 1)
            assert data == failed and error is None

            gap = {
                "status": "proved_with_replay_gaps", "verification_state": "unknown",
                "replay": {"gaps": 1},
                "summary": {"proven": 0, "obligations": 1}, "findings": [],
            }
            key, data, _, error = run_stub(gap, 0)
            assert key == "verified.elisa" and data is None and error == "exit-status-mismatch"
            key, data, _, error = run_stub(gap, 1)
            assert data == gap and error is None
        finally:
            refusal_census.BINARY = old_binary


provenance_guard_test()
subprocess_result_lattice_test()

print("refusal census: deterministic counts, result/exit parity, dogfood inclusion, timings, and provenance guards")
