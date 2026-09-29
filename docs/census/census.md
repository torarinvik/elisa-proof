# Refusal census

658 examples, 5833/7513 obligations proven.

| Count | Gate |
| ---: | --- |
| 411 | no-rule |
| 390 | function-summary-unverified: callee body has not established a verified executable summary |
| 137 | wrap-guard-goal |
| 127 | contract-proposition-type: kernel proposition formation rejected the term or operator |
| 124 | control-flow-analysis-budget: control-flow analysis exceeded its fact snapshot budget |
| 68 | contract-proposition-type: kernel proposition typing work budget exceeded |
| 47 | ambiguous-constant-goal |
| 39 | wrap-guard-fact |
| 28 | expression-unsupported: operator or index may dispatch to an unmodeled user protocol |
| 27 | borrow-call-opaque: a method-shaped call may write its receiver, and no summary maps a receiver |
| 27 | budget |
| 25 | loop-invariant-missing: loop has no invariant for symbolic verification |
| 24 | region-alias-unsupported: the binding's backing-region lifetime was not established; destruction has not been demonstrated |
| 22 | borrow-call-summary-unsupported: the checked callee resource summary could not be encoded for this call |
| 21 | borrow-call-opaque: a call argument carries a resource, but no converged callee resource summary is available |
| 20 | connective |
| 20 | expression-unsupported: unsupported runtime expression cannot enter a verified proof state |
| 20 | region-alias-unsupported: an sview value has no directly tracked live backing region |
| 17 | control-flow-analysis-budget: control-flow analysis exceeded its step budget |
| 17 | region-call-opaque: a region-polymorphic call has no converged lifetime summary |
| 14 | literal-width |
| 14 | region-call-opaque: a region-polymorphic call is not mapped to a verified caller region |
| 13 | resource-write-readonly: a whole-binding write requires a mutable resource binding |
| 12 | resource-use-after-move: a moved resource is used again |
| 9 | quantifier |
| 9 | region-alias-unsupported: region value aliases require a live, unmoved whole-binding source with the same tracked region |
| 7 | borrow-write-conflict: a write to a place overlapping a live borrow is not permitted by the proof resource state |
| 7 | contract-call-unsupported: logical contracts may use old(...) or calls to verified total pure functions |
| 7 | contract-expression-unsupported: floating-point parameter verification requires IEEE floating-point semantics |
| 7 | contract-placement-unsupported: this contract is not read at this position, so its claim would go unchecked |
| 6 | borrow-escape: a borrow cannot escape this lexical proof resource state |
| 6 | borrow-overlap-unproven: the access may overlap a live borrow; disjointness was not established, but a concrete overlap was not demonstrated |
| 6 | borrow-source-opaque: reference initializer is not a bounded static address-of borrow |
| 6 | non-comparison-goal |
| 6 | overloaded-operator |
| 6 | recursive-summary-unsupported: recursive executable summaries require matching checked lexicographic termination measures |
| 6 | structural-decreases-unproven: recursive call does not pass a binder from a matched strict subterm |
| 5 | frame-call-outside: callee changes a place outside the caller's changes frame |
| 5 | region-expression-unsupported: region value flows through an assignment without a lifetime summary |
| 4 | borrow-alias-conflict: mutable borrow conflicts with another live borrow of the same root |
| 4 | frame-write-outside: write is outside the function's changes frame |
| 4 | lemma-summary-unverified: lemma body has not established a verified proof summary |
| 4 | proof-hole: explicit `assert ?` proof hole is an open obligation |
| 4 | region-return-witness-unsupported: a region return must be tied to a replayed resource use or returned allocation |
| 4 | region-store-escape: a region-owned value may be assigned only from a directly tracked whole binding |
| 4 | resource-analysis-budget: resource-state analysis exceeded its bounded symbolic-state budget |
| 3 | borrow-source-opaque: a write through a mutable reference has no directly tracked target place |
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
| 2 | loop-condition-opaque: loop condition may mutate state and has no frame model |
| 2 | parallel-state-unsupported: parallel loop join semantics are not modeled by the proof state |
| 2 | proof-internal-name: source identifier collides with a proof-system internal name |
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
| 1 | region-expression-unsupported: region value flows through an expression without a lifetime summary |
| 1 | region-return-escape: the returned value lives in a region other than the declared return region |
| 1 | region-return-witness-unsupported: a mutable reference return must be tied to a replayed mutable reference formal |
| 1 | region-scope-unsupported: region block must introduce a fresh named lexical region |
| 1 | resource-use-after-move: a borrow cannot be created from a moved resource binding |
| 1 | structural-decreases-unproven: recursive call must preserve or strictly descend every inferred enum subject |

## Slowest examples

Wall time under the census's parallel load, so treat it as a ranking.

| Seconds | Example |
| ---: | --- |
| 87.22 | rejected_kernel_arena_cycle.elisa |
| 39.38 | kernel_intern_runtime.elisa |
| 17.80 | loop_state_joins.elisa |
| 9.84 | rejected_loop_state_joins.elisa |
| 8.51 | unsigned_resource_source_policy.elisa |
| 3.02 | field_places.elisa |
| 2.95 | dogfood_kernel_core.elisa |
| 2.05 | rejected_shared_fixed_borrows.elisa |
| 2.01 | rejected_budget.elisa |
| 1.82 | rejected_dogfood_kernel_core.elisa |
