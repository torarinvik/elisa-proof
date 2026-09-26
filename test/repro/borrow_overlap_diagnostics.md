# Conservative overlap is not a counterexample

The resource admission relation is intentionally a **may-overlap** relation:
without a replayable index-inequality witness, symbolic selectors might alias.
Unsupported selectors can also widen a borrow to the whole root, and string-view
borrows may conservatively cover a region. These abstractions must keep denying
potentially conflicting access, but cannot establish that concrete places overlap.

Previously, those denials were uniformly classified `disproved`. For example,
`unknown_widened_borrow_write.elisa` borrows an array element selected by another
array and writes element zero. The widened footprint alone does not tell us
whether those elements coincide. `rejected_borrow_symbolic_alias.elisa` similarly
lacks an index-separation proof, rather than furnishing a concrete overlap witness.

`resources/overlap_diagnostics.elisa` now separates diagnostic evidence from
admission. Exact whole-root/closed-index/field prefixes retain definite conflict
findings. Widened places, uncertain symbolic selectors and region-wide coverage
report `borrow-overlap-unproven` / `unknown`. Symbolic equalities not established
by this small diagnostic check may remain unknown even when provable elsewhere.

The additional `ProofResourcePlace.exact` bit is producer-side diagnostic metadata,
not a kernel premise or certificate flag. It propagates through field/index paths;
widening clears it. Neither the may-overlap admission predicate nor independent
resource replay uses it. Consequently, this change must not increase admitted
obligations, remove resource failures, or introduce replay gaps.

Run `python3 scripts/test_overlap_diagnostics.py` after building. The cases pair
uncertain symbolic/widened overlaps with definite whole-root, field, and literal
index conflicts; all remain failed verification attempts.

Validation: the pinned Stage0 build passed, all nine focused cases passed, and 45
baseline reports were unchanged. Fifty-one borrow/string-view fixtures kept their
expected verdicts with zero replay gaps; twenty existing detailed borrow-report
assertions also passed. The standalone replay-system audit completed in 56.55
seconds at 1,180,417 KB: 1,807 obligations, 860 certificates replayed, zero gaps,
and an `unsupported` verdict. This is not a self-verification claim.

## Move follow-up

The move-expression checker had a separate copy of the same diagnostic mistake.
`unknown_widened_borrow_move.elisa` constrains the selected borrowed element to
index one and moves index zero, yet previously reported a definite conflict after
widening the borrow. Moves now use the same evidence classifier. Moving a live
borrow handle remains a direct conflict, as do exact borrowed roots/descendants.
The conservative move refusal and resource-state transition rules are unchanged.

The pinned Stage0 rebuild and all twelve overlap regressions passed. Admission,
obligation counts, and replay summaries were identical across 42 borrow fixtures.
