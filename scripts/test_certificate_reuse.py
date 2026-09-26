#!/usr/bin/env python3
"""Exercise actual cache hits and premise invalidation through the public report."""
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent.parent


def report_for(name, expected_exit):
    process = subprocess.run(
        [str(ROOT / "build/elisa-proof"), "--json", str(ROOT / "examples" / (name + ".elisa"))],
        capture_output=True, text=True, timeout=60,
    )
    assert process.returncode == expected_exit, (name, process.stderr)
    report = json.loads(process.stdout)
    assert report["summary"]["semantic_errors"] == 0, name
    assert report["replay"]["gaps"] == 0, name
    assert report["replay"]["certificates"] == report["replay"]["replayed"], name
    return report


def main():
    positive = report_for("repeated_index_certificates", 0)
    assert positive["status"] == "proved"
    for rule in ("index-lower", "index-upper"):
        goals = [g for g in positive["goals"] if g["rule"] == rule]
        assert len(goals) == 2 and all(g["proven"] for g in goals)
        # Equal arena identities establish that this exercised reuse, not merely
        # two independent successful solver runs with equal printed expressions.
        for key in ("kernel_goal", "kernel_facts_start", "kernel_facts_count"):
            assert goals[0][key] == goals[1][key], (rule, key)
    assert positive["replay"]["certificates"] == positive["summary"]["obligations"]

    for name in ("rejected_repeated_index_mutation", "rejected_repeated_index_scope"):
        negative = report_for(name, 1)
        assert negative["status"] == "failed"
        goals = [g for g in negative["goals"] if g["rule"] == "index-upper"]
        assert len(goals) == 2 and goals[0]["proven"] and not goals[1]["proven"], name
        assert goals[0]["kernel_facts_start"] != goals[1]["kernel_facts_start"], name
        assert any(f["kind"] == "index-upper-unproven" for f in negative["findings"]), name
    print("certificate reuse: shared encodings, independent replay, mutation/scope invalidation passed")


if __name__ == "__main__":
    main()
