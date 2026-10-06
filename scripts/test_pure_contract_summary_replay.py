#!/usr/bin/env python3
"""Regression tests for pure-call summaries introduced from function preconditions."""
import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
REPLAY = Path(os.environ.get("ELISA_PROOF_REPLAY_BIN", ROOT / "build/elisa-proof-replay"))


def report(source: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="elisa-pure-call-replay-") as directory:
        path = Path(directory) / "probe.elisa"
        path.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [str(BINARY), "--json", str(path)],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(
            f"proof command did not return JSON (exit {result.returncode}): {result.stderr}"
        ) from error


def open_goals(result: dict) -> list[dict]:
    return [goal for goal in result["goals"] if not goal["proven"]]


def check_replay_is_gap_free(name: str, result: dict) -> None:
    assert result["replay"]["gaps"] == 0, (name, result["replay"])


def main() -> None:
    fixture = report((ROOT / "examples/pure_unfolding.elisa").read_text(encoding="utf-8"))
    assert fixture["status"] == "proved", fixture["summary"]
    assert fixture["summary"]["proven"] == fixture["summary"]["obligations"]
    check_replay_is_gap_free("pure_unfolding", fixture)
    with tempfile.TemporaryDirectory(prefix="elisa-pure-call-package-") as directory:
        package_path = Path(directory) / "pure-unfolding.json"
        exported = subprocess.run(
            [str(BINARY), "--package", str(ROOT / "examples/pure_unfolding.elisa")],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        package = json.loads(exported.stdout)
        assert exported.returncode == 0 and package["source"]["admissible"], package.get("source")
        assert len(package["theorems"]) == fixture["summary"]["obligations"]
        package_path.write_text(json.dumps(package), encoding="utf-8")
        replayed = subprocess.run(
            [str(REPLAY), str(package_path)],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        replay_result = json.loads(replayed.stdout)
        assert replayed.returncode == 0 and replay_result["status"] == "replayed", replay_result
        assert replay_result["summary"] == {
            "theorems": len(package["theorems"]),
            "replayed": len(package["theorems"]),
            "not_replayed": 0,
        }, replay_result["summary"]

    helper = "def is_digit(c: i64) -> bool:\n    return c >= 48 and c <= 57\n\n"
    positive = report(
        helper
        + "def digit_value(c: i64) -> i64:\n"
        + "    requires is_digit(c)\n"
        + "    ensures result >= 0 and result <= 9\n"
        + "    return c - 48\n"
    )
    assert not open_goals(positive), open_goals(positive)
    check_replay_is_gap_free("precondition-call-positive", positive)

    # A similarly named helper with a wider, verified condition must not inherit the
    # digit-specific range. At c == 58 the postcondition is false.
    wrong_condition = report(
        "def is_digit(c: i64) -> bool:\n"
        "    return c >= 48 and c <= 58\n\n"
        "def digit_value(c: i64) -> i64:\n"
        "    requires is_digit(c)\n"
        "    ensures result <= 9\n"
        "    return c - 48\n"
    )
    assert any(goal["name"] == "digit_value" for goal in open_goals(wrong_condition)), wrong_condition["goals"]
    check_replay_is_gap_free("wrong-helper-condition", wrong_condition)

    # Effectful helpers and wrappers around them are not logical call summaries. The
    # unsupported source contract must remain visible and cannot manufacture a fact.
    impure = report(
        "global mutable ticks: i64 = 0\n\n"
        "def impure_predicate(c: i64) -> bool:\n"
        "    ticks <- ticks + 1\n"
        "    return c == 10\n\n"
        "def impure_wrapper(c: i64) -> bool:\n"
        "    return impure_predicate(c)\n\n"
        "def caller(c: i64) -> i64:\n"
        "    requires impure_wrapper(c)\n"
        "    ensures result == 10\n"
        "    return c\n"
    )
    assert impure["status"] != "proved", impure["summary"]
    assert any(
        finding["kind"] == "contract-call-unsupported"
        for finding in impure["findings"]
    ), impure["findings"]
    leaked = [
        (goal["name"], fact["dependency"])
        for goal in impure["goals"]
        for fact in goal.get("fact_origins", [])
        if fact.get("kind") == "function-summary"
        and fact.get("dependency") in {"impure_predicate", "impure_wrapper"}
    ]
    assert not leaked, f"impure helper summary escaped into facts: {leaked}"
    check_replay_is_gap_free("impure-call-refusal", impure)
    print("pure precondition-call summaries replay exactly; false and effectful controls refuse")


if __name__ == "__main__":
    main()
