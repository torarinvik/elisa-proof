# Reusing repeated index checks

Indexing the same expression more than once can regenerate identical lower- and
upper-bound goals in one function. `proof_reuse_goal_attempt` limits its scan to
the most recent `PROOF_GOAL_MEMO_LOOKBACK` attempts and the current contiguous
function segment. It accepts only supported binary `index-lower` and `index-upper`
goals with structurally identical ordered facts, exact matching kernel fact roots,
and trace-backed premises. It does not reuse quantifier or general contract goals.

A hit reuses the arena goal and premise roots. A prior successful attempt gets a
fresh certificate/attempt record, so every use is independently replayed. Failed
non-budget attempts can avoid repeating the same deterministic search, while
budget-exhausted attempts are never cached. Mutation or branch-scope changes must
change the premises; those cases stay unproven in the regression corpus.

`test_certificate_reuse.py` checks equal kernel roots for repeated accesses,
independent replay counts, and invalidation after mutation and after leaving a
branch. The optimization is a bounded local memo; it does not provide persistent
cross-run caching or dependency invalidation.

The standalone replay corpus also exposed an internal source-backed `sview`
temporary in `proof_kernel_replay_pinned_constant`. Its name lookup now compares
validated identifier nodes directly, avoiding an untracked local view. The
full-source audit verifies that declaration again. Node bounds remain guarded
before each arena read so the independent kernel check covers the accesses.
