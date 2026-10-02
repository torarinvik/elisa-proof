#!/usr/bin/env python3
"""Struct invariants are refused until verified: positive, adversarial, malformed and budget cases."""
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BINARY = ROOT / "build/elisa-proof"
KIND = "declaration-unsupported"


def run(path):
    result = subprocess.run([str(BINARY), "--json", str(path)], capture_output=True, text=True, timeout=600)
    return json.loads(result.stdout)


def probe(source):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "probe.elisa"
        path.write_text(source)
        return run(path)


def invariant_findings(report):
    return [finding for finding in report["findings"] if finding["kind"] == KIND and "struct invariant" in finding["message"]]


def main():
    positive = run(ROOT / "examples/struct_without_invariant.elisa")
    assert positive["status"] == "proved", "a struct without an invariant must still prove"
    assert not invariant_findings(positive), "a struct without an invariant was refused"

    # Adversarial: a construction that breaks the invariant must never be reported verified.
    rejected = run(ROOT / "examples/rejected_struct_invariant.elisa")
    assert rejected["status"] != "proved", "rejected_struct_invariant must not prove"
    assert [finding["line"] for finding in invariant_findings(rejected)] == [4], "refusal must name the struct"

    # Even an invariant every construction satisfies is refused: nothing checks it yet.
    kept = probe("struct P:\n    low: i64\n    high: i64\n    invariant low <= high\n\ndef f() -> P:\n    return P{low: 1, high: 2}\n")
    assert kept["status"] != "proved" and len(invariant_findings(kept)) == 1, "unchecked invariant reported verified"

    # Malformed placement: a struct inside a module is still found.
    nested = probe("module M:\n    struct P:\n        x: i64\n        invariant x >= 0\n")
    assert nested["status"] != "proved" and len(invariant_findings(nested)) == 1, "module struct invariant missed"

    # Budget: one refusal per struct however many invariants it states.
    clauses = "".join(f"    invariant x >= {index}\n" for index in range(40))
    many = probe("struct P:\n    x: i64\n" + clauses)
    assert len(invariant_findings(many)) == 1, "expected one refusal per struct"
    print("struct invariants: positive, adversarial, malformed and budget cases pass")


if __name__ == "__main__":
    main()
