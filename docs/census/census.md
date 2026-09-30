# Refusal census

Census date: 2026-09-30 (UTC).

691 examples and 1 dogfood proof units; 9262/12265 obligations proven.

Unreadable inputs: 11.

| Count | First refusal gate / diagnostic |
| ---: | --- |
| 1023 | function-summary-unverified: callee body has not established a verified executable summary |
| 563 | no-rule |
| 363 | control-flow-analysis-budget: control-flow analysis exceeded its fact snapshot budget |
| 207 | contract-proposition-type: kernel proposition typing work budget exceeded |
| 198 | wrap-guard-goal |
| 158 | contract-proposition-type: kernel proposition formation rejected the term or operator |
| 58 | expression-unsupported: operator or index may dispatch to an unmodeled user protocol |
| 58 | region-alias-unsupported: the binding's backing-region lifetime was not established; destruction has not been demonstrated |
| 56 | region-alias-unsupported: an sview value has no directly tracked live backing region |
| 56 | wrap-guard-fact |
| 55 | ambiguous-constant-goal |
| 53 | borrow-call-opaque: a call argument carries a resource, but no converged callee resource summary is available |
| 47 | control-flow-analysis-budget: control-flow analysis exceeded its step budget |
| 47 | region-call-opaque: a region-polymorphic call has no converged lifetime summary |
| 40 | borrow-call-summary-unsupported: the checked callee resource summary could not be encoded for this call |
| 39 | budget |
| 39 | loop-invariant-missing: loop has no invariant for symbolic verification |
| 35 | borrow-call-opaque: a method-shaped call may write its receiver, and no summary maps a receiver |
| 35 | resource-write-readonly: a whole-binding write requires a mutable resource binding |
| 26 | expression-unsupported: unsupported runtime expression cannot enter a verified proof state |
| 24 | region-call-opaque: a region-polymorphic call is not mapped to a verified caller region |
| 21 | connective |
| 17 | region-alias-unsupported: region value aliases require a live, unmoved whole-binding source with the same tracked region |
| 15 | region-expression-unsupported: region value flows through an assignment without a lifetime summary |
| 14 | literal-width |
| 12 | resource-use-after-move: a moved resource is used again |
| 11 | resource-analysis-budget: resource-state analysis exceeded its bounded symbolic-state budget |
| 10 | region-store-escape: a region-owned value may be assigned only from a directly tracked whole binding |
| 9 | quantifier |
| 8 | recursive-summary-unsupported: recursive executable summaries require matching checked lexicographic termination measures |
| 7 | borrow-source-opaque: a write through a mutable reference has no directly tracked target place |
| 7 | borrow-write-conflict: a write to a place overlapping a live borrow is not permitted by the proof resource state |
| 7 | contract-call-unsupported: logical contracts may use old(...) or calls to verified total pure functions |
| 7 | contract-expression-unsupported: floating-point parameter verification requires IEEE floating-point semantics |
| 7 | contract-placement-unsupported: this contract is not read at this position, so its claim would go unchecked |
| 7 | non-comparison-goal |
| 7 | proof-internal-name: source identifier collides with a proof-system internal name |
| 6 | borrow-escape: a borrow cannot escape this lexical proof resource state |
| 6 | borrow-overlap-unproven: the access may overlap a live borrow; disjointness was not established, but a concrete overlap was not demonstrated |
| 6 | borrow-source-opaque: reference initializer is not a bounded static address-of borrow |
| 6 | overloaded-operator |
| 6 | structural-decreases-unproven: recursive call does not pass a binder from a matched strict subterm |
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
| 3 | region-expression-unsupported: region value flows through an expression without a lifetime summary |
| 3 | region-use-after-destroy: a region-owned binding is accessed after its region was destroyed |
| 2 | borrow-call-alias: mutable call arguments overlap while the callee is running |
| 2 | borrow-move-conflict: a live borrow prevents moving the borrowed place |
| 2 | borrow-mutable-source: mutable borrow requires a writable source binding |
| 2 | effect-row-exceeded: a called function declares an effect outside this function's row |
| 2 | import-error: one or more Elisa include files could not be read |
| 2 | parallel-state-unsupported: parallel loop join semantics are not modeled by the proof state |
| 2 | region-alias-unsupported: a returned reference must retain the region established by the callee summary |
| 2 | resource-use-after-move: a moved resource is written again |
| 1 | borrow-write-conflict: a write through a mutable reference overlaps a live borrow |
| 1 | contract-proposition-type: kernel proposition statement nesting exceeded its bounded representation |
| 1 | effect-call-opaque: a called function has no imported effect row |
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
- `kernel_sview_lifetimes_runtime.elisa`: timeout
- `lemma_summary_replay_runtime.elisa`: timeout
- `marker_dispatch_runtime.elisa`: timeout
- `tactic_runtime.elisa`: timeout

## Toolchain provenance

Proof binary SHA-256: `2f69c532b37c15f48f2e81d238f8ad5cf93dba4a0322eb16f237e9365356a007`; compiler stage: `stage1`; compiler revision: `61ea11eb29a8ed2fa9a59c07acd1c2c09f9d255f`; proof source HEAD: `907c18254e6e1030de66313c48423d41cf766d96`.
