# Qualified call-summary module identity

## Finding

Function-summary replay selected a source declaration using its name and declaration line, but
the recorded call was checked only against the last segment of its module qualifier. With
`Gate::Inner::bounded` as the real call, a forged summary could substitute
`Elsewhere::Inner::bounded` and retain the same final module segment. The source summary and its
postcondition still matched, so the old replay check accepted the forged owner witness.

The focused harness reproduced this before the fix: after replacing both the summary result binding
and the corresponding postcondition expression, `proof_replay_fact_trace_entry` accepted the
wrong-parent call (the test exited with its dedicated failure code 17).

## Fix and regression

Commit `d4c0fee0` binds qualified function-summary witnesses to the full declared module path. The
replay check compares nested `Ast::Expr.Scope` segments against the target owner without allocating
a flattened name. A one-segment qualifier may match a nested module only when its parent is the
caller's lexical module or one of its ancestors. Bare-call disambiguation remains constrained to
the unique declaration or exact caller/callee module match.

The Stage1 source-level regression contains `Gate::Inner::bounded` plus an unrelated
`Elsewhere::Inner` module with the same leaf name. It confirms all of the following:

- the original qualified call-summary witness replays;
- changing the summary's `result` binding and postcondition together to
  `Elsewhere::Inner::bounded(x)` is rejected;
- the same-leaf wrong-module mutation of a deterministic-call trace is rejected;
- restoring the original trace and bindings returns replay to success;
- the existing malformed summary-result mutation continues to be rejected.

The harness is registered in `scripts/test.d/01-setup-and-python-suites.sh` and compiles the
current checker/replay source directly. It does not use a potentially stale built proof binary.

## Toolchain and validation

- Compiler revision: `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`.
- Stage1 product SHA-256: `96eca8200bb268ea5cc1635a66d6b0da0cd85611331319c3227362d9421c2947`.
- Matching runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
- `stage1_provenance.py check` reported the product current for the compiler revision above.
- `python3 scripts/tests/test_deterministic_call_qualified_replay.py`: passed after the fix.
- `python3 scripts/check_source_length.py`: passed.
- `bash -n scripts/test.d/01-setup-and-python-suites.sh`: passed.
- `git diff --check`: passed.

## Remaining boundary

This closes one same-leaf module substitution in executable function-summary replay; it does not
close R-005. Alias-qualified calls and all caller/callee declaration identities, ordered actuals,
reference places, state versions, contract/effect/footprint bindings, and cross-checking against an
immutable source snapshot still require coverage. The full test matrix and a coherent current
proof/replay product build were not run as part of this focused change.
