# Nested loop replay source scopes (2026-10-08)

Clean paired source `7d89ab5a` still has two replay gaps in the original
`examples/loop_exit_frame.elisa` fixture: the inner loop invariant entry and
preservation certificates of `nested_outer_fact`. They consume a local `k`
declared in the outer loop body, rather than at function top level.

The shared bounded `loop_scopes.elisa` traversal locates a unique executable
source loop and its lexical statement list. Entry invariant reconstruction,
source guard/invariant authentication and self-update source reconstruction
now use that lookup. Nested local admission separately counts unique source
declarations, rejects shadowing by binders/blocks/patterns and unsupported
initializer scopes, and retains the existing consumer scope and liveness checks.
Traversal refuses depth 64 or work 4,096. It never treats a preservation
certificate as an entry certificate or admits a binding from an unrelated body.

Frozen compiler `52d60fcf` and matching runtime compile the O0 harnesses:

- `python3.14 scripts/test_nested_loop_scope_source.py`: all nine original
  certificates independently replay; wrong header line, duplicate loop line,
  depth/work limit, duplicate nested declaration and entry/preservation controls
  pass, including preservation refusal when its context flag is false.
- `python3.14 scripts/test_loop_entry_expanded_source.py`: original binding
  replay, preservation refusal and all eleven existing forged source controls pass.

An early audit shell command masked the executable status by continuing to a
subsequent diff check. Direct execution revealed the remaining top-level-only
uniqueness requirement; the nested declaration check repairs it. Final evidence
above uses subprocess `check=True` on both compilation and execution.

Clean paired product build, complete original loop-exit positive/adversarial
regression and uncached engine sweep are pending. Full compatibility and
production promotion remain open.
