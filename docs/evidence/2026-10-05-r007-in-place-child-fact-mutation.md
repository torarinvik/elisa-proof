# R-007 in-place post-check child-context mutation

The tactic runtime harness now closes a disjunction case tree, confirms composed branch
certificate replay, then replaces the left child's final captured assumption with the right
child's assumption in the existing `initial_facts` array. The context length is asserted unchanged.
Branch-transition replay must refuse the mutated child. This complements the existing control
that replaces the child's entire context array and specifically exercises post-check mutation of
an existing context slot.

## Validation

- Proof source base: `4e8e3fbb`; working branch: `codex/luna-r007-stale-context`.
- Stage1 compiler source revision: `ecd26eb776ef72e6c25bb0cec7129344acf0f2fd` (the compiler
  checkout had unrelated uncommitted changes during the build).
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
- Focused command compiled `examples/tactic_runtime.elisa` at O0 with Stage1, linked it with the
  runtime object and profiler hooks, and executed it. Compilation, linking, and execution passed;
  harness exit status was 0. Harness SHA-256:
  `84df2ecbf953996a7e5ca7712e9b6717c4d4512e5201954d49eee9b589200b14`.
- `git diff --check`: passed.

This checks one branch-transition path and one in-place assumption replacement. It does not
establish immutable context IDs, stable binder IDs, arena generations, or coverage of other
tactic and scratch-storage paths. No implementation defect was observed in this path.
