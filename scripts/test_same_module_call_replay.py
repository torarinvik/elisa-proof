"""Repeated callees resolve from source without weakening spans or actuals."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

BINARY = qualified_test_binary.proof_test_binary(ROOT)
BASE = """module A:
    public:
        def step(value: i64) -> i64:
            ensure result == value
            return value
        def caller(value: i64) -> i64:
            requires value >= 1 and value <= 100
            ensure result == value
            return step(value)
module B:
    public:
        def step(value: i64) -> i64:
            ensure result == value + 1
            return value + 1
"""
NESTED_NEAREST = """module Root:
    public:
        def step(value: i64) -> i64:
            ensure result == value + 1
            return value + 1
        module Mid:
            public:
                def step(value: i64) -> i64:
                    ensure result == value
                    return value
                module Inner:
                    public:
                        def caller(value: i64) -> i64:
                            requires value >= 1 and value <= 100
                            ensure result == value
                            return step(value)
"""
NESTED_REPEATED_LEAF_OWNER = """module Root:
    public:
        module Left:
            public:
                module Inner:
                    public:
                        def step(value: i64) -> i64:
                            ensure result == value + 1
                            return value + 1
                        def caller(value: i64) -> i64:
                            requires value >= 1 and value <= 100
                            requires step(value) == value + 1
                            ensure result == value + 1
                            return step(value)
        module Right:
            public:
                module Inner:
                    public:
                        def step(value: i64) -> bool:
                            ensure result == (value >= 0)
                            return value >= 0
"""
NESTED_CONTRACT_BARE_ROOT_CALL = """def nonnegative(value: i64) -> bool:
    ensure result == (value >= 0)
    return value >= 0

module Root:
    public:
        module Sibling:
            public:
                def nonnegative(value: i64) -> bool:
                    return value == 0
        module Inner:
            public:
                def caller(value: i64) -> i64:
                    requires nonnegative(value)
                    ensure result == value
                    return value
                def qualified_caller(value: i64) -> i64:
                    requires Root::Sibling::nonnegative(value)
                    ensure result == value
                    return value
"""
for name, source, accepted in (
    ("same-module", BASE, True),
    ("nearest-enclosing-module", NESTED_NEAREST, True),
    ("nested-repeated-leaf-owner", NESTED_REPEATED_LEAF_OWNER, True),
    ("nested-contract-bare-root-callee", NESTED_CONTRACT_BARE_ROOT_CALL, True),
    ("qualified", BASE.replace("return step(value)", "return A::step(value)"), True),
    ("wrong-module", BASE.replace("return step(value)", "return B::step(value)"), False),
    ("changed-argument", BASE.replace("return step(value)", "return step(value + 1)"), False),
):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.elisa"
        path.write_text(source)
        for route in ("--json", "--function-json"):
            args = [BINARY, route] + (["caller"] if route == "--function-json" else []) + [str(path)]
            run = subprocess.run(args, capture_output=True, text=True, timeout=60)
            report = json.loads(run.stdout)
            # Focused replay must resolve a bare callee in the caller's exact module scope;
            # unrelated same-named functions must neither block nor replace that dependency.
            expected_acceptance = accepted
            assert run.returncode == (0 if expected_acceptance else 1), (name, route, report["summary"])
            if not expected_acceptance and route == "--function-json":
                assert any(f["kind"] == "function-summary-unverified" for f in report["findings"])
            assert report["summary"]["semantic_errors"] == 0
            assert report["replay"]["gaps"] == 0, (name, route, report["replay"])
            assert not report["trust"]["trusted_assumptions"]
    print("same-module call replay:", name, "accepted" if accepted else "refused", "with full and focused source replay")

# A local value named like a global function must block bare-call fallback. The source
# frontend rejects invoking the integer parameter; replay must never type it as the root
# declaration merely because that declaration exists in the global signature table.
SHADOWED_CONTRACT_BARE_CALL = """def nonnegative(value: i64) -> bool:
    return value >= 0

module Root:
    public:
        module Inner:
            public:
                def caller(nonnegative: i64) -> i64:
                    requires nonnegative(0)
                    ensure result == 0
                    return 0
"""
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "shadowed.elisa"
    path.write_text(SHADOWED_CONTRACT_BARE_CALL)
    run = subprocess.run([BINARY, "--json", str(path)], capture_output=True, text=True, timeout=60)
    report = json.loads(run.stdout)
    assert run.returncode == 1, ("shadowed-bare-contract-callee", report["summary"])
    assert report["summary"]["semantic_errors"] > 0, report["summary"]
    assert not report["trust"]["trusted_assumptions"]
print("same-module call replay: shadowed contract callee refused")
