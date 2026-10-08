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


def compact_report_test():
    full = {
        "status": "failed", "verification_state": "unknown",
        "summary": {"proven": 1, "obligations": 2, "unused": [1] * 1000},
        "replay": {"gaps": 0, "certificates": [1] * 1000},
        "findings": [{"refusal_gate": "budget", "kind": "ensure-unproven",
                      "message": "bounded", "trace": [1] * 1000},
                     {"kind": None, "message": None}, {}],
        "kernel": {"arena": [1] * 1000}, "certificates": [1] * 1000,
    }
    compact = refusal_census.census_report(full)
    assert "kernel" not in compact and "certificates" not in compact
    assert compact["summary"] == {"proven": 1, "obligations": 2}
    assert compact["replay"] == {"gaps": 0}
    assert "trace" not in compact["findings"][0]
    assert compact["findings"][1] == {"kind": None, "message": None}
    assert compact["findings"][2] == {}
    for report in (full, compact):
        entry = {"x": {"report": report, "seconds": 1, "error": None}}
        summary = refusal_census.summarize(entry, 1, 0, "2026-10-08", None)
        if report is full:
            original = summary
        else:
            assert summary == original


def input_closure_guard_test():
    import contextlib
    import io
    from census_input_identity import include_argument, input_identity
    assert include_argument('# include "a b.elisa"') == "a b.elisa"
    assert include_argument("{$I 'a b.elisa'}") == "a b.elisa"
    assert include_argument('{$include leaf.elisa}') == "leaf.elisa"
    assert include_argument('include\t"leaf.elisa"') is None
    assert include_argument('include "leaf.elisa" # comment') is None
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "examples").mkdir()
        source = root / "examples/unit.elisa"
        leaf = root / "leaf.elisa"
        source.write_text('include "../leaf.elisa"\n')
        leaf.write_text('{$include examples/unit.elisa}\n')  # cycle remains bounded
        chain = root / "chain"
        chain.mkdir()
        for index in range(66):
            (chain / f"{index}.elisa").write_text(f'include "{index + 1}.elisa"\n')
        bounded = input_identity([chain / "0.elisa"])
        assert bounded["files"][str(chain / "65.elisa")] == {"include_depth_limit": 64}
        assert str(chain / "66.elisa") not in bounded["files"]
        # All roots start at depth zero: a deep dependency independently selected
        # as an input still contributes its bytes and dependencies to the identity.
        with patch("census_input_identity.DEPENDENCY_FILE_LIMIT", 2):
            try:
                input_identity([chain / "0.elisa"])
            except RuntimeError as error:
                assert "file budget" in str(error)
            else:
                raise AssertionError("dependency file budget was ignored")
        independent = input_identity([chain / "0.elisa", chain / "65.elisa"])
        assert "sha256" in independent["files"][str(chain / "65.elisa")]
        initial = input_identity([source])
        assert len(initial["files"]) == 2
        leaf.write_text('changed\n')
        assert initial != input_identity([source])
        leaf.unlink()
        missing = input_identity([source])
        assert "read_error" in missing["files"][str(leaf)]
        leaf.write_text('restored\n')
        assert missing != input_identity([source])
        binary = root / "proof"
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)

        def mutate(path, timeout):
            leaf.write_text("changed during census\n")
            return "unit.elisa", {"summary": {"proven": 0, "obligations": 0},
                                  "findings": []}, 0, None

        output = root / "output"
        with patch.object(refusal_census, "ROOT", root), \
             patch.object(refusal_census, "BINARY", binary), \
             patch.object(refusal_census, "DOGFOOD_SOURCES", ()), \
             patch.object(refusal_census, "toolchain_identity", return_value={}), \
             patch.object(refusal_census, "run", side_effect=mutate), \
             patch.object(sys, "argv", ["census", str(output), "--workers", "1"]), \
             contextlib.redirect_stderr(io.StringIO()) as errors:
            try:
                refusal_census.main()
            except SystemExit as error:
                assert error.code == 2
            else:
                raise AssertionError("changed dependency was published")
        assert "included sources changed" in errors.getvalue()
        assert not (output / "census.json").exists()


def snapshot_source_test():
    import shutil
    from types import SimpleNamespace
    from census_input_identity import compiler_export_digest
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary).resolve()
        live = base / "live"
        snapshot = base / "export/elisa-proof"
        compiler = snapshot.parent / "Elisa-compiler"
        for name in ("src", "examples"):
            (live / name).mkdir(parents=True)
            (live / name / "unit.elisa").write_text("initial\n")
        shutil.copytree(live, snapshot)
        for name in ("src", "elisacore_std"):
            (compiler / name).mkdir(parents=True)
            (compiler / name / "unit.elisa").write_text("compiler source\n")
        (compiler / ".rev").write_text("rev123\n")
        binary = base / "proof"
        manifest = {"frontend": {"revision": "rev123"},
                    "compiler": {"source_revision": "rev123",
                                 "source_tree_sha256": compiler_export_digest(compiler)}}
        Path(str(binary) + ".manifest.json").write_text(json.dumps(manifest))
        with patch.object(refusal_census, "ROOT", live), \
             patch.object(refusal_census, "BINARY", binary), \
             patch.dict(os.environ, {"ELISA_PROOF_CENSUS_SOURCE_ROOT": str(snapshot)}):
            refusal_census.validate_census_source_root()
            assert refusal_census.census_source_path(live / "examples/unit.elisa") == snapshot / "examples/unit.elisa"
            report = {"status": "proved", "verification_state": "proved",
                      "summary": {"proven": 1, "obligations": 1},
                      "replay": {"gaps": 0}, "findings": []}
            with patch.object(refusal_census.subprocess, "run",
                              return_value=SimpleNamespace(stdout=json.dumps(report), returncode=0)) as execute:
                key, data, _, error = refusal_census.run(live / "examples/unit.elisa", 10)
                assert key == "unit.elisa" and data == report and error is None
                assert execute.call_args.args[0][-1] == str(snapshot / "examples/unit.elisa")
            for target in (snapshot / "src/unit.elisa", snapshot / "examples/unit.elisa",
                           compiler / "src/unit.elisa", compiler / ".rev"):
                original = target.read_bytes()
                target.write_bytes(original + b"changed\n")
                try:
                    refusal_census.validate_census_source_root()
                except RuntimeError:
                    pass
                else:
                    raise AssertionError(f"changed snapshot was accepted: {target}")
                finally:
                    target.write_bytes(original)
            link = compiler / "src/linked.elisa"
            link.symlink_to(compiler / "src/unit.elisa")
            try:
                refusal_census.validate_census_source_root()
            except RuntimeError:
                pass
            else:
                raise AssertionError("linked compiler source was accepted")


provenance_guard_test()
subprocess_result_lattice_test()
compact_report_test()
input_closure_guard_test()
snapshot_source_test()

print("refusal census: deterministic counts, result/exit parity, dogfood inclusion, timings, and provenance guards")
