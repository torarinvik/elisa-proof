"""Versioned, source-pinned workload inventory for proof performance work.

This module validates corpus identity and outcome metadata. It does not run a
proof, qualify a compiler pair, or claim a performance baseline.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts" / "perf_luna_corpus.v1.json"
SCHEMA = "elisa-proof-workload-corpus"
VERSION = 1
REQUIRED_WORKLOADS = frozenset({
    "accept", "refusal", "symbolic_quantifier", "rejected_symbolic_quantifier",
    "congruence", "rejected_congruence", "kernel_core", "dogfood_kernel_core",
    "rejected_dogfood_kernel_core", "bounded_model_work_budget", "for_invariant",
    "branch_join", "rejected_branch_join", "effect_containment", "borrow_call_summary",
})
OUTCOME_CATEGORIES = frozenset({"proved", "expected_refusal", "mixed_budget_boundary"})
CENSORED_STATES = frozenset({
    "censored", "timeout", "timed_out", "truncated", "incomplete", "skipped",
    "not_run", "cancelled", "failed_to_start",
})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CorpusError(ValueError):
    """The reviewed corpus or its observed result is incomplete or stale."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CorpusError(message)


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=False, capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise CorpusError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_corpus(path: Path = MANIFEST) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CorpusError(f"cannot read workload corpus {path}: {error}") from error
    _require(isinstance(value, dict), "corpus root must be an object")
    _require(value.get("schema") == SCHEMA, "unsupported corpus schema")
    _require(value.get("version") == VERSION, "unsupported corpus version")
    revision = value.get("source_revision")
    _require(isinstance(revision, str)
             and re.fullmatch(r"[0-9a-f]{40,64}", revision) is not None,
             "source_revision must be a full lowercase Git object ID")
    entries = value.get("workloads")
    _require(isinstance(entries, list) and entries, "workloads must be a nonempty array")
    seen: set[str] = set()
    for entry in entries:
        _validate_entry_shape(entry, seen)
    missing = REQUIRED_WORKLOADS - seen
    extra = seen - REQUIRED_WORKLOADS
    _require(not missing, f"required workload cases are missing: {sorted(missing)}")
    _require(not extra, f"unreviewed workload cases are present: {sorted(extra)}")
    return value


def _validate_entry_shape(entry: Any, seen: set[str]) -> None:
    _require(isinstance(entry, dict), "each workload must be an object")
    name = entry.get("name")
    _require(isinstance(name, str) and name and name not in seen,
             "workload names must be nonempty and unique")
    seen.add(name)
    path = entry.get("path")
    _require(isinstance(path, str) and path and "\\" not in path
             and not Path(path).is_absolute() and ".." not in Path(path).parts,
             f"{name}: workload path must be repository-relative")
    outcome = entry.get("expected_outcome")
    _require(isinstance(outcome, dict), f"{name}: missing expected_outcome")
    category = outcome.get("category")
    _require(isinstance(category, str) and category in OUTCOME_CATEGORIES,
             f"{name}: unknown semantic outcome category")
    proof_status = outcome.get("proof_status")
    _require(isinstance(proof_status, str) and proof_status in {"proved", "failed"},
             f"{name}: proof_status must be proved or failed")
    _require(type(outcome.get("exit_code")) is int and outcome["exit_code"] in {0, 1},
             f"{name}: expected exit_code must be 0 or 1")
    _require((outcome["proof_status"] == "proved") == (outcome["exit_code"] == 0),
             f"{name}: proof status and expected exit code disagree")
    _require((category == "proved") == (proof_status == "proved"),
             f"{name}: semantic category and proof status disagree")
    if category == "mixed_budget_boundary":
        _require(isinstance(entry.get("expected_semantics"), dict),
                 f"{name}: mixed-outcome workload needs function-level semantic expectations")
    files = entry.get("source_files")
    _require(isinstance(files, list) and files, f"{name}: source_files must be nonempty")
    input_paths = _validate_file_identities(files, name, "source")
    _require(path in input_paths, f"{name}: primary workload source is absent from provenance")
    oracles = entry.get("expectation_sources")
    _require(isinstance(oracles, list) and oracles,
             f"{name}: expected semantic outcome needs a checked-in oracle source")
    _validate_file_identities(oracles, name, "expectation oracle")
    role = entry.get("role")
    _require(isinstance(role, str) and role in {"timed_fixture", "project_workload"},
             f"{name}: invalid workload role")


def _validate_file_identities(files: list[Any], name: str, label: str) -> set[str]:
    paths: set[str] = set()
    for source in files:
        _require(isinstance(source, dict), f"{name}: {label} identity must be an object")
        source_path, digest = source.get("path"), source.get("sha256")
        _require(isinstance(source_path, str) and source_path and "\\" not in source_path
                 and not Path(source_path).is_absolute()
                 and ".." not in Path(source_path).parts,
                 f"{name}: {label} path must be repository-relative")
        _require(source_path not in paths, f"{name}: duplicate {label} path {source_path}")
        paths.add(source_path)
        _require(isinstance(digest, str) and SHA256_RE.fullmatch(digest) is not None,
                 f"{name}: {label} SHA-256 is malformed")
    return paths


def validate_sources(corpus: dict[str, Any], *, root: Path = ROOT) -> None:
    """Verify every listed input against both the pinned commit and checkout bytes."""
    revision = corpus["source_revision"]
    _git(root, "cat-file", "-e", revision)
    head = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    ancestor = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", revision, head],
        check=False, capture_output=True,
    )
    _require(ancestor.returncode == 0,
             "pinned source revision is not an ancestor of the current committed HEAD")
    for entry in corpus["workloads"]:
        for source in (*entry["source_files"], *entry["expectation_sources"]):
            source_path = source["path"]
            expected = source["sha256"]
            try:
                current = (root / source_path).read_bytes()
            except OSError as error:
                raise CorpusError(f"{entry['name']}: missing workload source {source_path}") from error
            pinned = _git(root, "show", f"{revision}:{source_path}")
            _require(_sha256(pinned) == expected,
                     f"{entry['name']}: manifest hash is stale for pinned source {source_path}")
            _require(_sha256(current) == expected,
                     f"{entry['name']}: checked-out source is stale or dirty: {source_path}")


def validate_result(entry: dict[str, Any], result: dict[str, Any]) -> None:
    """Reject censored/incomplete evidence before comparing semantic outcomes."""
    _require(isinstance(result, dict), f"{entry['name']}: result must be an object")
    state = result.get("state")
    _require(isinstance(state, str), f"{entry['name']}: result is missing complete-run status")
    _require(state not in CENSORED_STATES,
             f"{entry['name']}: censored result state {state!r} is not evidence")
    report_status = result.get("status")
    _require(report_status != "censored" and result.get("timing_valid") is not False
             and not result.get("censored_failures"),
             f"{entry['name']}: benchmark report contains censored failures")
    _require(state == "complete", f"{entry['name']}: result is missing complete-run status")
    truncation_flags = [result[key] for key in
                        ("stdout_truncated", "program_stdout_truncated") if key in result]
    _require(bool(truncation_flags) and all(flag is False for flag in truncation_flags),
             f"{entry['name']}: missing or truncated stdout cannot establish an outcome")
    expected_exit = entry["expected_outcome"]["exit_code"]
    _require(type(result.get("exit_code")) is int and result["exit_code"] == expected_exit,
             f"{entry['name']}: result exit code differs from the corpus expectation")
    _require(result.get("proof_status") == entry["expected_outcome"]["proof_status"],
             f"{entry['name']}: result proof status differs from the corpus expectation")
    _require(result.get("semantic_category") == entry["expected_outcome"]["category"],
             f"{entry['name']}: result semantic category differs from the corpus expectation")
    if "expected_semantics" in entry:
        _require(result.get("semantic_details") == entry["expected_semantics"],
                 f"{entry['name']}: function-level semantic outcome differs from the corpus expectation")
    _require(type(result.get("replay_gaps")) is int and result["replay_gaps"] == 0,
             f"{entry['name']}: result is not replay-closed")
    requested, completed = result.get("requested_samples"), result.get("completed_samples")
    _require(type(requested) is int and requested > 0 and type(completed) is int
             and completed == requested,
             f"{entry['name']}: sample set is missing, partial, or censored")


def validate_all(root: Path = ROOT, path: Path = MANIFEST) -> dict[str, Any]:
    corpus = load_corpus(path)
    validate_sources(corpus, root=root)
    return corpus


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    corpus = validate_all(root=args.root, path=args.manifest)
    print(f"workload corpus v{corpus['version']} valid: {len(corpus['workloads'])} cases, "
          f"source revision {corpus['source_revision']}")
    print("This validates workload identity only; it is not a performance baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
