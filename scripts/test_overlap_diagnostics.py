#!/usr/bin/env python3
"""Distinguish conservative footprints from demonstrated resource overlaps."""
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
BINARY = ROOT / "build/elisa-proof"
CASES = {
    "unknown_widened_borrow_move": ("borrow-overlap-unproven", "unknown"),
    "rejected_borrow_move": ("borrow-move-conflict", "disproved"),
    "rejected_borrow_move_parent": ("borrow-move-conflict", "disproved"),
    "unknown_widened_borrow_write": ("borrow-overlap-unproven", "unknown"),
    "rejected_borrow_symbolic_alias": ("borrow-overlap-unproven", "unknown"),
    "rejected_borrow_dynamic_alias": ("borrow-overlap-unproven", "unknown"),
    "rejected_borrow_dynamic_multi_alias": ("borrow-overlap-unproven", "unknown"),
    "rejected_exact_index_borrow_write": ("borrow-write-conflict", "disproved"),
    "rejected_borrow_write": ("borrow-write-conflict", "disproved"),
    "rejected_borrow_field_write": ("borrow-write-conflict", "disproved"),
    "rejected_borrow_index_alias": ("borrow-alias-conflict", "disproved"),
    "rejected_borrow_multi_index_alias": ("borrow-alias-conflict", "disproved"),
}


def main():
    for name, expected in CASES.items():
        process = subprocess.run(
            [str(BINARY), "--json", str(ROOT / "examples" / (name + ".elisa"))],
            capture_output=True, text=True, timeout=60,
        )
        report = json.loads(process.stdout)
        assert process.returncode == 1, name
        assert report["status"] == "failed", name
        if name in {"unknown_widened_borrow_write", "unknown_widened_borrow_move", "rejected_exact_index_borrow_write"}:
            assert report["summary"]["semantic_errors"] == 0, name
        findings = {(f["kind"], f["status"]) for f in report["findings"]}
        assert expected in findings, (name, findings)
        if expected[1] == "unknown":
            assert all(status != "disproved" for _, status in findings), (name, findings)
        assert report["replay"]["gaps"] == 0, name
        assert report["replay"]["certificates"] == report["replay"]["replayed"], name
    print(f"{len(CASES)} overlap diagnostic regressions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
