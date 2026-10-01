# Refusal census

Census date: 2026-10-01 (UTC).

712 examples and 1 dogfood proof units; 8027/10417 obligations proven.

Unreadable inputs: 12.

| Count | First refusal gate |
| ---: | --- |
| 562 | no-rule |
| 176 | wrap-guard-goal |
| 53 | ambiguous-constant-goal |
| 38 | budget |
| 36 | wrap-guard-fact |
| 24 | connective |
| 14 | literal-width |
| 11 | overloaded-operator |
| 9 | quantifier |
| 8 | non-comparison-goal |
| 1 | ambiguous-constant-fact |

## Non-goal diagnostics

| Count | Diagnostic |
| ---: | --- |
| 745 | function-summary-unverified: callee body has not established a verified executable summary |
| 246 | control-flow-analysis-budget: control-flow analysis exceeded its fact snapshot budget |
| 174 | contract-proposition-type: kernel proposition formation rejected the term or operator |
| 48 | expression-unsupported: operator or index may dispatch to an unmodeled user protocol |
| 44 | region-alias-unsupported: an sview value has no directly tracked live backing region |
| 42 | borrow-call-opaque: a call argument carries a resource, but no converged callee resource summary is available |
| 41 | region-alias-unsupported: the binding's backing-region lifetime was not established; destruction has not been demonstrated |
| 36 | control-flow-analysis-budget: control-flow analysis exceeded its step budget |
| 36 | region-call-opaque: a region-polymorphic call has no converged lifetime summary |
| 33 | borrow-call-summary-unsupported: the checked callee resource summary could not be encoded for this call |
| 32 | loop-invariant-missing: loop has no invariant for symbolic verification |
| 31 | borrow-call-opaque: a method-shaped call may write its receiver, and no summary maps a receiver |
| 24 | resource-write-readonly: a whole-binding write requires a mutable resource binding |
| 23 | expression-unsupported: unsupported runtime expression cannot enter a verified proof state |
| 21 | region-call-opaque: a region-polymorphic call is not mapped to a verified caller region |
| 13 | region-alias-unsupported: region value aliases require a live, unmoved whole-binding source with the same tracked region |
| 12 | resource-analysis-budget: resource-state analysis exceeded its bounded symbolic-state budget |
| 12 | resource-use-after-move: a moved resource is used again |
| 10 | region-expression-unsupported: region value flows through an assignment without a lifetime summary |
| 7 | borrow-write-conflict: a write to a place overlapping a live borrow is not permitted by the proof resource state |
| 7 | contract-call-unsupported: logical contracts may use old(...) or calls to verified total pure functions |
| 7 | contract-placement-unsupported: this contract is not read at this position, so its claim would go unchecked |
| 7 | expression-unsupported: source-overloaded operator may mutate proof-visible state without a modeled effect summary |
| 7 | proof-internal-name: source identifier collides with a proof-system internal name |
| 7 | recursive-summary-unsupported: recursive executable summaries require matching checked lexicographic termination measures |
| 7 | region-store-escape: a region-owned value may be assigned only from a directly tracked whole binding |
| 6 | borrow-escape: a borrow cannot escape this lexical proof resource state |
| 6 | borrow-overlap-unproven: the access may overlap a live borrow; disjointness was not established, but a concrete overlap was not demonstrated |
| 6 | borrow-source-opaque: reference initializer is not a bounded static address-of borrow |
| 6 | structural-decreases-unproven: recursive call does not pass a binder from a matched strict subterm |
| 5 | borrow-source-opaque: a write through a mutable reference has no directly tracked target place |
| 5 | frame-call-outside: callee changes a place outside the caller's changes frame |
| 4 | borrow-alias-conflict: mutable borrow conflicts with another live borrow of the same root |
| 4 | frame-write-outside: write is outside the function's changes frame |
| 4 | lemma-summary-unverified: lemma body has not established a verified proof summary |
| 4 | loop-condition-opaque: loop condition may mutate state and has no frame model |
| 4 | proof-hole: explicit `assert ?` proof hole is an open obligation |
| 4 | region-return-witness-unsupported: a region return must be tied to a replayed resource use or returned allocation |
| 3 | call-old-opaque: callee ensure depends on a pre-state that is not tracked across calls |
| 3 | frame-preserve-write: write violates a preserved function place |
| 3 | index-bounds-opaque: indexed access has no statically tracked collection bound |
| 3 | lemma-recursive-unsupported: recursive lemma summaries require matching checked lexicographic termination measures |
| 3 | parse-error: source could not be parsed; verification was not attempted |
| 3 | region-contract-unsupported: region-owned expressions are not admitted in logical contracts |
| 3 | region-destroy-live-borrow: a region cannot be destroyed while a borrowed view or reference to it is still live |
| 3 | region-expression-unsupported: a region-owned expression must be bound or explicitly rejected at this resource boundary |
| 3 | region-use-after-destroy: a region-owned binding is accessed after its region was destroyed |
| 2 | borrow-call-alias: mutable call arguments overlap while the callee is running |
| 2 | borrow-move-conflict: a live borrow prevents moving the borrowed place |
| 2 | borrow-mutable-source: mutable borrow requires a writable source binding |
| 2 | effect-row-exceeded: a called function declares an effect outside this function's row |
| 2 | import-error: one or more Elisa include files could not be read |
| 2 | parallel-state-unsupported: parallel loop join semantics are not modeled by the proof state |
| 2 | region-alias-unsupported: a returned reference must retain the region established by the callee summary |
| 2 | region-expression-unsupported: region value flows through an expression without a lifetime summary |
| 2 | resource-use-after-move: a moved resource is written again |
| 1 | borrow-write-conflict: a write through a mutable reference overlaps a live borrow |
| 1 | contract-proposition-type: kernel proposition statement nesting exceeded its bounded representation |
| 1 | effect-call-opaque: a called function has no imported effect row |
| 1 | expression-unsupported: unsupported match guard cannot enter a verified proof state |
| 1 | expression-unsupported: value-match guard cannot enter a verified proof state |
| 1 | frame-preserve-violated: callee changes a place declared preserved by the caller |
| 1 | frame-spec-invalid: frame clauses must name a function parameter or parameter field |
| 1 | frame-spec-invalid: header changes metadata names a non-parameter root |
| 1 | frame-write-opaque: write target may alias a framed parameter but its root is not tracked |
| 1 | getelse-recovery-nonterminating: get/try recovery must terminate on every path |
| 1 | lemma-impure: lemma bodies may not mutate or return |
| 1 | lemma-return: lemmas are proof-only and may not return runtime values |
| 1 | loop-invariant-scope: for-loop invariants may refer only to bindings that remain in scope after the loop |
| 1 | pattern-unsupported: match pattern bindings are not modeled for proof-state substitution |
| 1 | proof-impure: proof assertions may not evaluate executable calls or ownership transfers |
| 1 | region-destroy-unsupported: destroy must name the innermost active tracked region |
| 1 | region-return-escape: the returned value lives in a region other than the declared return region |
| 1 | region-return-witness-unsupported: a mutable reference return must be tied to a replayed mutable reference formal |
| 1 | region-scope-unsupported: region block must introduce a fresh named lexical region |
| 1 | resource-use-after-move: a borrow cannot be created from a moved resource binding |
| 1 | structural-decreases-unproven: recursive call must preserve or strictly descend every inferred enum subject |

## Unreadable inputs

- `field_equality_runtime.elisa`: timeout
- `kernel_arena_runtime.elisa`: timeout
- `kernel_comparison_runtime.elisa`: timeout
- `kernel_congruence_runtime.elisa`: timeout
- `kernel_effect_runtime.elisa`: timeout
- `kernel_projection_runtime.elisa`: timeout
- `kernel_proposition_admission_runtime.elisa`: timeout
- `kernel_replay_standalone.elisa`: timeout
- `kernel_sview_lifetimes_runtime.elisa`: timeout
- `lemma_summary_replay_runtime.elisa`: timeout
- `marker_dispatch_runtime.elisa`: timeout
- `tactic_runtime.elisa`: timeout

## Toolchain provenance

Proof binary SHA-256: `da4d489179ee6d84741913ee7358bb28a3a7f2b6a5007efec62d01c490b34fc4`; compiler stage: `stage1`; compiler revision: `d8b5d305ec99a9d2238e035b871d9fd4e9835603`; proof source HEAD: `3e5b4d345e445e0f81e5261abc3395da765f6ba3`.
