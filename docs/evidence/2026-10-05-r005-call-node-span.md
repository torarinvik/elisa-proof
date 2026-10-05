# R-005 exact call-node span replay

The deterministic-call replay check matched the call's callee and ordered actuals against the
source expression, but ignored the call node's source span. A trace could therefore retain the
same call semantics while naming a different AST node position.

Replay now compares all six position fields (`line`, `column`, `offset`, `end_line`, `end_column`,
and `end_offset`) on the matched call node. The in-memory Stage1 harness changes only the nested
call's starting offset, re-encodes the forged trace, requires replay to reject it, restores the
original trace, and requires it to replay again. Existing same-leaf wrong-module controls remain in
the same harness.

## Validation

- `python3 scripts/tests/test_deterministic_call_qualified_replay.py`: passed with fresh Stage1
  provenance for compiler revision `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`.
- Harness output: `qualified deterministic-call replay: qualified owner accepted; wrong call-span
  and same-leaf wrong-module forgeries rejected`.

This establishes exact call-node span identity for the tested deterministic-call trace path. It does
not cover the other P0.8 fields, package-level differential replay, or call identity for other trace
kinds.
