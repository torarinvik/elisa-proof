# R-007 quantifier and branch boundary audit

This is a narrow source and runtime audit, not completion of R-007.

## Scope and observations

- `proof_kernel_replay_substitute` in `src/proof/kernel_replay/fact_model.elisa` does not descend into a nested quantifier body when the binder shadows the substituted name. When the binder is different, it refuses with `substitution-under-quantifier`; its source comment records that the arena lacks binding levels and alpha-renaming. This closes the obvious name-capture path for this substitution helper, with reduced proof coverage.
- Dictionary quantifier substitution uses two markers for simultaneous substitution. It refuses identical binders and refuses marker names already present in the node arena (`quantifiers_and_arena.elisa`).
- Disjunctive premise replay in `resource_model.elisa` creates separate left and right fact arrays and replaces the split premise independently. Existing variant-exclusion and conditional-ensure tests exercise branch refusal/independence, but do not establish a global immutable context identity.

## Pinned O2 validation

Built from proof HEAD `04b5e20ab40dfb4b7c657a51a6d1d72957144c5f` with strict O2, pinned Stage1 revision `7b27fa312c5af923f044f6ee0e5e1de4f811f595`, arm64 macOS. Binary SHA-256: `178f5380b00cacebaba6926d7d517982079afcc63ca3336e91a8875eb14dd971`.

- `scripts/test_symbolic_quantifiers.py`: passed; bounded quantifier positives replay, capture/shadow and other adversarial cases remain unproven, malformed range and fact-budget controls refuse.
- `scripts/test_variant_exclusion.py`: passed; sibling variants are excluded and ambiguous enum control refuses.
- `scripts/test_conditional_ensure_replay_gap.py`: passed; conditional ensure gaps refuse or replay fully, and wrong-guard control remains unproved.

## Remaining R-007 gate

This audit did not mutate serialized certificates or arenas after validation, probe reused scratch handles across independently checked contexts, exercise escaping eigenvariables, or prove exact context membership/stale-context-ID behavior. Binder names are still used instead of distinct binder IDs. Those gates and broader positive nested-quantifier/branch coverage remain open; no soundness defect was established by these checks.
