# Refusal census

Census date: 2026-10-08 (UTC).

1126 examples and 1 dogfood proof units; 80168/177649 obligations proven.

Unreadable inputs: 6.

| Count | First refusal gate |
| ---: | --- |
| 10625 | unknown |
| 1583 | wrap-guard-goal |
| 418 | wrap-guard-fact |
| 271 | budget |
| 212 | connective |
| 157 | ambiguous-constant-goal |
| 61 | quantifier |
| 38 | non-comparison-goal |
| 19 | literal-width |
| 18 | overloaded-operator |
| 2 | opaque-call-goal |

## Non-goal diagnostics

| Count | Diagnostic |
| ---: | --- |
| 23045 | function-summary-unverified: callee body has not established a verified executable summary |
| 16320 | borrow-call-opaque: a method-shaped call may write its receiver, and no summary maps a receiver |
| 10815 | borrow-call-opaque: a call argument carries a resource, but no converged callee resource summary is available |
| 10582 | expression-unsupported: operator or index may dispatch to an unmodeled user protocol |
| 5351 | borrow-source-opaque: reference initializer is not a bounded static address-of borrow |
| 4551 | control-flow-analysis-budget: control-flow analysis exceeded its fact snapshot budget |
| 3104 | region-alias-unsupported: an sview value has no directly tracked live backing region |
| 2697 | contract-proposition-type: kernel proposition formation rejected the term or operator |
| 1720 | loop-invariant-missing: loop has no invariant for symbolic verification |
| 1492 | region-return-witness-unsupported: a mutable reference return must be tied to a replayed mutable reference formal |
| 1351 | borrow-escape: a borrow cannot escape this lexical proof resource state |
| 1287 | recursive-summary-unsupported: recursive executable summaries require matching checked lexicographic termination measures |
| 1005 | expression-unsupported: unsupported runtime expression cannot enter a verified proof state |
| 678 | borrow-call-summary-unsupported: the checked callee resource summary could not be encoded for this call |
| 670 | resource-write-readonly: a whole-binding write requires a mutable resource binding |
| 648 | captured-block-unsupported: a captured block's write-back is havocked rather than modeled |
| 647 | contract-expression-unsupported: parameter numeric type alias cannot be resolved uniquely |
| 637 | region-call-opaque: a region-polymorphic call has no converged lifetime summary |
| 630 | control-flow-analysis-budget: control-flow analysis exceeded its step budget |
| 605 | contract-expression-unsupported: local numeric type alias cannot be resolved uniquely |
| 417 | borrow-escape: a newly created borrow is assigned across a binding boundary |
| 401 | index-bounds-opaque: indexed access has no statically tracked collection bound |
| 395 | contract-expression-unsupported: parameter refinement type alias cannot be resolved uniquely |
| 363 | region-alias-unsupported: the binding's backing-region lifetime was not established; destruction has not been demonstrated |
| 282 | borrow-source-opaque: a write through a mutable reference has no directly tracked target place |
| 268 | borrow-source-opaque: borrow target is not a live proof binding |
| 252 | structural-decreases-unproven: recursive call does not pass a binder from a matched strict subterm |
| 159 | contract-expression-unsupported: return numeric type alias cannot be resolved uniquely |
| 153 | contract-expression-unsupported: return refinement type alias cannot be resolved uniquely |
| 138 | resource-analysis-budget: resource-state analysis exceeded its bounded symbolic-state budget |
| 128 | region-call-opaque: a region-polymorphic call is not mapped to a verified caller region |
| 128 | region-expression-unsupported: region value flows through an assignment without a lifetime summary |
| 105 | borrow-source-opaque: address-of value enters a non-reference binding |
| 89 | region-alias-unsupported: region value aliases require a live, unmoved whole-binding source with the same tracked region |
| 62 | region-store-escape: a region-owned value may be assigned only from a directly tracked whole binding |
| 57 | loop-condition-opaque: loop condition may mutate state and has no frame model |
| 47 | effect-call-opaque: a called function has no unambiguous imported effect row |
| 38 | effect-call-opaque: complete executable source-call coverage or lexical dispatch could not be reconstructed |
| 34 | pattern-unsupported: match pattern bindings are not modeled for proof-state substitution |
| 32 | resource-use-after-move: a moved resource is used again |
| 30 | effect-call-opaque: an extern effect row lacks complete source-bound declaration metadata |
| 21 | structural-decreases-unproven: captured value block is not structurally certified |
| 20 | region-expression-unsupported: region value flows through an expression without a lifetime summary |
| 15 | contract-call-unsupported: logical contracts may use old(...) or calls to verified total pure functions |
| 12 | contract-proposition-type: kernel typing declaration environment exceeded its bounded representation |
| 10 | structural-decreases-unproven: recursive call must preserve or strictly descend every inferred enum subject |
| 8 | proof-internal-name: source identifier collides with a proof-system internal name |
| 7 | borrow-write-conflict: a write to a place overlapping a live borrow is not permitted by the proof resource state |
| 7 | contract-placement-unsupported: this contract is not read at this position, so its claim would go unchecked |
| 7 | expression-unsupported: source-overloaded operator may mutate proof-visible state without a modeled effect summary |
| 6 | borrow-overlap-unproven: the access may overlap a live borrow; disjointness was not established, but a concrete overlap was not demonstrated |
| 6 | slice-bounds-opaque: slice has no statically tracked collection bound |
| 5 | effect-row-exceeded: a called function declares an effect outside this function's row |
| 5 | frame-call-outside: callee changes a place outside the caller's changes frame |
| 5 | source-obligation-inventory: a tracked Boolean-literal assert-by target or proof step is unsupported, omitted, duplicated, falsely claimed, or unreplayed |
| 4 | borrow-alias-conflict: mutable borrow conflicts with another live borrow of the same root |
| 4 | borrow-contract-unsupported: resource-bearing expressions are not admitted in logical contracts |
| 4 | frame-write-outside: write is outside the function's changes frame |
| 4 | lemma-summary-unverified: lemma body has not established a verified proof summary |
| 4 | parse-error: source could not be parsed; verification was not attempted |
| 4 | proof-hole: explicit `assert ?` proof hole is an open obligation |
| 4 | region-destroy-live-borrow: a region cannot be destroyed while a borrowed view or reference to it is still live |
| 4 | region-return-witness-unsupported: a region return must be tied to a replayed resource use or returned allocation |
| 4 | region-use-after-destroy: a region-owned binding is accessed after its region was destroyed |
| 4 | source-obligation-inventory: a supported source postcondition has no distinct proof attempt |
| 3 | borrow-call-alias: mutable call arguments overlap while the callee is running |
| 3 | call-old-opaque: callee ensure depends on a pre-state that is not tracked across calls |
| 3 | frame-preserve-write: write violates a preserved function place |
| 3 | import-error: one or more Elisa include files could not be read |
| 3 | lemma-recursive-unsupported: recursive lemma summaries require matching checked lexicographic termination measures |
| 3 | region-contract-unsupported: region-owned expressions are not admitted in logical contracts |
| 3 | region-expression-unsupported: a region-owned expression must be bound or explicitly rejected at this resource boundary |
| 2 | borrow-move-conflict: a live borrow prevents moving the borrowed place |
| 2 | borrow-mutable-source: mutable borrow requires a writable source binding |
| 2 | lemma-ambiguous: another lemma has the same name; lemma names must be unique for their summaries to be used |
| 2 | parallel-state-unsupported: parallel loop join semantics are not modeled by the proof state |
| 2 | region-alias-unsupported: a returned reference must retain the region established by the callee summary |
| 2 | region-allocation-unsupported: new[r] produces a region reference and requires a reference-bearing destination |
| 2 | resource-use-after-move: a moved resource is written again |
| 1 | borrow-readonly-write: a write through an immutable reference is not permitted by the proof resource state |
| 1 | borrow-write-conflict: a write through a mutable reference overlaps a live borrow |
| 1 | contract-expression-unsupported: logical contract uses an unsupported expression form |
| 1 | contract-proposition-type: kernel proposition statement nesting exceeded its bounded representation |
| 1 | declaration-unsupported: struct invariant is not verified: it is neither established at construction nor preserved by field writes |
| 1 | expression-unsupported: unsupported match guard cannot enter a verified proof state |
| 1 | expression-unsupported: value-match guard cannot enter a verified proof state |
| 1 | frame-preserve-violated: callee changes a place declared preserved by the caller |
| 1 | frame-spec-invalid: frame clauses must name a function parameter or parameter field |
| 1 | frame-spec-invalid: header changes metadata names a non-parameter root |
| 1 | getelse-recovery-nonterminating: get/try recovery must terminate on every path |
| 1 | lemma-impure: lemma bodies may not mutate or return |
| 1 | lemma-return: lemmas are proof-only and may not return runtime values |
| 1 | loop-decreases-unproven: continue path requires a separate checked termination step |
| 1 | loop-invariant-scope: for-loop invariants may refer only to bindings that remain in scope after the loop |
| 1 | proof-impure: proof assertions may not evaluate executable calls or ownership transfers |
| 1 | proof-unknown: proof blocks may contain only assert facts |
| 1 | region-destroy-unsupported: destroy must name the innermost active tracked region |
| 1 | region-return-escape: the returned value lives in a region other than the declared return region |
| 1 | region-scope-unsupported: region block must introduce a fresh named lexical region |
| 1 | resource-use-after-move: a borrow cannot be created from a moved resource binding |

## Unreadable inputs

- `deterministic_call_trace_replay_runtime.elisa`: timeout
- `field_equality_runtime.elisa`: timeout
- `lemma_summary_replay_runtime.elisa`: timeout
- `marker_dispatch_runtime.elisa`: timeout
- `required_reference_replay_runtime.elisa`: timeout
- `tactic_runtime.elisa`: timeout

## Toolchain provenance

Proof binary SHA-256: `1b90c66bc534d382019eb4b8b740428d234f82df8c938cd716d7b203132c4dfb`; compiler stage: `stage1`; compiler revision: `96761822e6469efb929c5d50a804bb765f6bc3f7`; proof source HEAD: `None`.
