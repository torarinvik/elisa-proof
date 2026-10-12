#!/usr/bin/env python3
"""Regression tests for proof admission and call edges from signature contracts."""
import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))


def report(source: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="elisa-signature-contract-") as directory:
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


def has_finding(result: dict, kind: str, name: str) -> bool:
    return any(
        finding["kind"] == kind and finding["name"] == name
        for finding in result["findings"]
    )


def main() -> None:
    positive = report(
        "type Nonnegative = i64 where self >= 0\n\n"
        "def identity(value: Nonnegative) -> Nonnegative:\n"
        "    return value\n"
    )
    assert positive["status"] == "proved", positive["summary"]
    assert positive["replay"]["gaps"] == 0, positive["replay"]

    # The overloaded Eq implementation makes the source precondition true for every input.
    # If the generated signature fact reaches the kernel as built-in equality, this function's
    # false ensures is proved from value == 1.
    overloaded_precondition = report(
        "protocol Eq:\n"
        "    def __eq__(self: Self, other: Self) -> bool\n\n"
        "impl Eq for i64:\n"
        "    def __eq__(self: i64, other: i64) -> bool:\n"
        "        return true\n\n"
        "type One = i64 where self == 1\n\n"
        "def require_one(value: One) -> i64:\n"
        "    ensures result >= 1\n"
        "    return value\n"
    )
    assert has_finding(
        overloaded_precondition, "contract-expression-unsupported", "require_one"
    ), overloaded_precondition["findings"]
    caller_goals = [
        goal for goal in overloaded_precondition["goals"]
        if goal["name"] == "require_one"
    ]
    assert caller_goals and any(not goal["proven"] for goal in caller_goals), caller_goals
    assert not any(
        origin["kind"] == "precondition"
        for goal in caller_goals
        for origin in goal["fact_origins"]
    ), caller_goals
    assert overloaded_precondition["replay"]["gaps"] == 0, overloaded_precondition["replay"]

    # A return refinement becomes a signature ensure. A source-level overloaded equality must
    # not be checked or published with the kernel's primitive equality semantics.
    overloaded_signature_ensure = report(
        "protocol Eq:\n"
        "    def __eq__(self: Self, other: Self) -> bool\n\n"
        "impl Eq for i64:\n"
        "    def __eq__(self: i64, other: i64) -> bool:\n"
        "        return false\n\n"
        "type One = i64 where self == 1\n\n"
        "def returns_two() -> One:\n"
        "    return 2\n"
    )
    assert overloaded_signature_ensure["status"] != "proved", overloaded_signature_ensure["summary"]
    assert has_finding(
        overloaded_signature_ensure, "contract-expression-unsupported", "returns_two"
    ), overloaded_signature_ensure["findings"]
    assert overloaded_signature_ensure["replay"]["gaps"] == 0, overloaded_signature_ensure["replay"]

    # Body contract admission must use the same source operator witness policy as signature
    # contracts; this assertion is false under the source Eq implementation.
    overloaded_body_contract = report(
        "protocol Eq:\n"
        "    def __eq__(self: Self, other: Self) -> bool\n\n"
        "impl Eq for i64:\n"
        "    def __eq__(self: i64, other: i64) -> bool:\n"
        "        return false\n\n"
        "def body_contract() -> i64:\n"
        "    ensures (1 == 1) == true\n"
        "    return 0\n"
    )
    assert overloaded_body_contract["status"] != "proved", overloaded_body_contract["summary"]
    assert has_finding(
        overloaded_body_contract, "contract-expression-unsupported", "body_contract"
    ), overloaded_body_contract["findings"]
    assert overloaded_body_contract["replay"]["gaps"] == 0, overloaded_body_contract["replay"]

    # This cycle has no recursive call in its body. The only edge is the predicate call
    # introduced from the parameter refinement, which still belongs in the function SCC graph.
    signature_only_cycle = report(
        "type RecursiveInput = i64 where recursive_predicate(self)\n\n"
        "def recursive_predicate(value: RecursiveInput) -> bool:\n"
        "    return true\n"
    )
    recursive = [
        declaration for declaration in signature_only_cycle["declaration_details"]
        if declaration["name"] == "recursive_predicate"
        and declaration["kind"] == "function"
    ]
    assert recursive and recursive[0]["recursive"], recursive
    assert not recursive[0]["verified"], recursive
    assert signature_only_cycle["replay"]["gaps"] == 0, signature_only_cycle["replay"]

    print("signature contracts preserve primitive semantics and contribute call-graph edges")


if __name__ == "__main__":
    main()
