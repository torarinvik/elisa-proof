# R-007 sibling-context mutation regression

This adds one focused executable regression to the existing tactic runtime harness. It creates
two disjunction-case child states, appends a new fact to the left child after construction, and
checks that neither the right child nor the parent fact count changes. This observes fact-array
isolation for that construction path; it does not prove general immutability, context identity, or
assumption discharge soundness.

## Validation identity

- Proof source revision: `7432d4abdb1c98d19abd78ecdfec9aca138f1667`.
- Compiler: pinned Stage1 `7b27fa312c5af923f044f6ee0e5e1de4f811f595`, binary SHA-256
  `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`.
- Runtime object SHA-256:
  `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
- Compiled `examples/tactic_runtime.elisa` at O0, linked against the pinned runtime and profiler
  hooks, and executed successfully (exit 0). The resulting harness SHA-256 is
  `2fad01cef1f37b9db26e806cc50d6c093996155f53dea75985b743f00ce2eb27`.
- `git diff --check`: passed.

The mutation test checks array-count independence after a child mutation. It does not attempt to
forge a solved child or replay a mutated certificate; those remain separate gates.
