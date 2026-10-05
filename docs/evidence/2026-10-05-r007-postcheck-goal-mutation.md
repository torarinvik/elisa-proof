# R-007 post-check tactic goal mutation control

The executable tactic runtime harness now builds a conjunction branch tree, closes both child
goals, and confirms that the untouched branch certificate replays. It then replaces the left
child's captured `initial_goal` with a different AST value and requires composed branch
certificate replay to refuse. The control is intentionally limited to one post-check child-goal
mutation; it does not establish general AST backing-store immutability or stable context IDs.

## Validation

- Proof source commit: `ef5dea6b` (`test: reject post-check tactic goal mutation`).
- Stage1 compiler revision reported by the freshness check: `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`.
- Stage1 compiler binary SHA-256: `96eca8200bb268ea5cc1635a66d6b0da0cd85611331319c3227362d9421c2947`.
- Matching runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
- Focused command compiled `examples/tactic_runtime.elisa` at O0 with Stage1, linked it with the
  matching runtime and profiler hooks, and executed it. The compile, link, and harness all
  succeeded; harness exit status was 0. The harness SHA-256 is
  `21bcdd90b34845dbf609a4cc2b5286d6f33aac17e86e38d6a487e85e7a108dc7`.
- The compile invocation was
  `ELISA_RUNTIME_OBJ="$PWD/../Elisa-compiler/build/runtime/elisacore_runtime.o" "$PWD/../Elisa-compiler/scripts/elisac_stage1.sh" -emit obj -O0 -o /tmp/r007-context-postcheck/tactic-runtime.o examples/tactic_runtime.elisa`.
  It was linked with `clang` plus the matching runtime object and
  `../Elisa-compiler/test/parity/profile_hooks.c` compiled to
  `/tmp/r007-context-postcheck/profile-hooks.o`, using `scripts/link_flags.sh`'s
  `elisa_link_native`; then `/tmp/r007-context-postcheck/tactic-runtime` exited 0.
- `git diff --check`: passed.
- `python3 scripts/test_tactic_branch_regions.py`: not run successfully because this checkout
  has no `build/elisa-proof` binary (`FileNotFoundError`). The runtime mutation control above
  does not depend on that CLI binary.

The existing R-007 gaps remain: arbitrary shared AST backing-store mutation, stale generation
handles, distinct binder IDs, escaping eigenvariables, general alpha-renaming, concurrency,
reentrancy, and complete coverage across tactic and scratch-storage paths.
