# R-008 source-backed trust-boundary path audit — 2026-10-05

## Scope and conclusion

This is a focused source-path audit supplement to
[`2026-10-05-r008-trust-register.md`](2026-10-05-r008-trust-register.md) and
[`KERNEL_INVENTORY.md`](../../KERNEL_INVENTORY.md). It follows the principal theorem construction
and admission routes into their checkers, source adapters, test families, and available artifact
identity evidence. It does not claim a complete TCB audit, rule-by-rule soundness proof, or
exhaustive constructor inventory. R-008 remains open.

Source paths below are relative to the repository root. Names refer to the current inspected
working-tree source, which was not a clean snapshot during this review. No source code was changed.

## Construction-to-admission routes

| Route | Construction and source premises | Admission/checker | Solver/tactic boundary | Tests and identity evidence | Unmapped trust question |
|---|---|---|---|---|---|
| Ordinary contracts and proof obligations | `src/proof/check/*` collects requires/ensures, branch/loop facts, immutable local bindings and call/lemma summaries; `src/proof/kernel.elisa::proof_kernel_encode_expression` lowers supported AST expressions into `ProofKernelNode` arenas. `src/proof/model/report_recording.elisa` records goal attempts, certificate roots and captured facts. `src/proof/check/certificate_reuse.elisa` may reuse an exact goal/fact match. | `src/proof/replay/fact_trace_validation.elisa::proof_replay_certificate_with_stack` checks certificate/attempt identity, source-AST-to-arena correspondence, fact trace provenance, dependencies and then dispatches via `proof_replay_certificate_rule_valid` to the public checker in `src/proof/kernel_replay/api.elisa`. Derived facts re-enter replay through `src/proof/replay/certificate_validation.elisa`; boundary facts dispatch through `boundary_trace_shapes.elisa` plus kind-specific validators. | Search, simplification, arithmetic and lemma discovery propose facts/certificates outside the kernel (`src/proof/linear/*`, `src/proof/check/*`). Admission depends on trace validity and replay, not the producer's `found` result. The externally advertised empty assumptions list is a report field, not proof that all premises are source-derived. | `scripts/test.d/01a-kernel-replay-audit.sh`, `01b-proof-report-and-tactic-boundaries.sh`, `scripts/test_kernel_inventory.py`, `scripts/test_replay_dependency_row.py`, and the positive/negative proof fixtures under `examples/`. Artifact identity is not established by this source review; see “Build and artifact identity”. | No independent formal derivation proves every source adapter fact sound. Global constants, function/lemma summaries, type bounds, loop facts, local substitutions, and branch joins each rely on distinct source walkers. Exact completeness of all statement/obligation sites is still open (R-004); semantics of every encoded expression constructor and correspondence to Elisa compiler typing are not proven here. |
| Quantifier and checked-access certificates | The same expression encoder emits quantifier and checked-index/get roots; obligation discovery and range/binder interpretation live in `src/proof/check/*` and `src/proof/kernel.elisa`. | `src/proof/replay/fact_trace_validation.elisa` dispatches `quantifier-forall`, `quantifier-exists`, `checked-index`, and `checked-get`; specialized checks enter `src/proof/kernel_replay/api.elisa` and then their private implementations. Arena typing/shape validation precedes the rule. | Quantifier candidate/range selection and rewrite/search are untrusted. The kernel rechecks formation, binder substitution and the specialized rule; producer completeness and source binder identity are separate assumptions. | Quantifier, index, and standalone replay tests in `scripts/test.d/01a-kernel-replay-audit.sh`, `scripts/test.d/03-index-and-loop-facts.sh`, `scripts/test_kernel_logical_equations.sh`, and `scripts/test_portable_replay.py`. | Binder identity is still substantially name-based; post-validation mutation, eigenvariable escape, and systematic constructor-level quantifier mutation are open (R-007). Checked access correctness also depends on accurately modeling Elisa integer widths, bounds and runtime trap semantics. |
| Resource safety | `src/proof/resources/{statement_checker,expression_checker,borrows_and_bindings,state_and_regions,region_flow,call_regions,sview_certificates,return_witnesses,places_and_calls}.elisa` emits transition nodes while walking parsed source, signatures, ownership, borrows, regions and call sites. `src/proof/certificate_admission.elisa::proof_add_resource_goal_attempt` admits only a `resource-safety` root, `resource-v1` version marker and an inert source mirror `true`, with no proposition facts. | `src/proof/replay/fact_trace_validation.elisa` checks resource event facts; `src/proof/kernel_replay/api.elisa` validates the arena and dispatches to `proof_kernel_replay_resource_report_impl` and resource transition validators. `KERNEL_INVENTORY.md` enumerates the resource event kinds and fact-free leaves. | No SMT result is a resource proof. The source trace producer maps AST ownership/borrow operations into a finite event trace; the resource checker replays that trace. | `scripts/test.d/02-regions-and-rewrites.sh`, `scripts/test.d/05-03-resource-call-region-safety.sh`, `scripts/test_portable_replay.py`, `scripts/test_stride_index_resource.py`, plus region/sview/forwarded-frame focused suites. The 2026-10-05 focused R-049 note reports an isolated Stage1 product but leaves raw certificate-place forgery and indexed forwarding open. | Highest semantic dependency is the source-walker-to-transition relation: compiler ownership/lifetime rules, alias/place normalization, reference forwarding, and event ordering. Tests cover selected paths, not equivalence for all expression/statement constructors. Runtime/compiler undefined behavior and unsafe/extern code assumptions are not represented by the root. |
| Effect containment | `src/proof/check/effect_containment.elisa::proof_check_effect_containment` obtains the declared row, enumerates calls, resolves local or extern metadata, checks source declaration identity and exact source call-set coverage, and emits `effect`, `effect-row`, `effect-call`, `effect-containment` nodes. `certificate_admission.elisa` admits this specialized root without proposition facts. | `src/proof/replay/fact_trace_validation.elisa` revalidates source call/effect coverage with `proof_replay_effect_source_valid`, then dispatches to `proof_kernel_replay_effect_report_with_workspace`; the replay-side validation checks row containment. | Solver and tactic results do not establish effect containment. This is an AST-derived call/effect summary plus specialized replay. | `scripts/test_extern_effect_containment.py`, `scripts/test_extern_effect_rows_native.sh`, effect-loop tests, and positive package case `effect_containment` in `scripts/test_portable_replay.py`. | Source-call-set completeness, lexical dispatch, dynamically indirect calls, compiler lowering, and extern/runtime honesty remain assumptions or explicit refusal cases. A complete source/runtime effect semantics is not established by rows alone. |
| Structural termination | `src/proof/check/flow_and_type_model.elisa` tracks typed pattern/subterm witnesses and emits `structural-argument`, `structural-edge`, and `structural-safety` nodes. `certificate_admission.elisa` requires the root/version marker `structural-v1`. | `src/proof/kernel_replay/api.elisa` dispatches to the structural checker, which validates ranking shape and strict descent independently of the AST walker. | No SMT or tactic success is sufficient; termination candidate discovery is source-side, serialized relation replay is kernel-side. | `scripts/test_portable_replay.py` includes `implicit_structural_decreases`; termination-related proof fixtures exercise positives and refusals. | The key unmapped premise is whether every recursive call in every control-flow path is represented and whether typed pattern identity guarantees actual strict subterm semantics for every Elisa type/pattern form. Ranking soundness does not establish runtime/extern termination outside the checked body. |
| Tactic/script construction | `src/proof/tactics/*` mutates a `ProofTacticState` and records action/post-state traces; `src/app/cli_tactics.elisa` binds an optional tactic script to a source goal. `src/app/repair.elisa` can generate candidates. | `src/proof/tactics/kernel_replay.elisa` deterministically replays accepted/rejected transitions; `src/proof/kernel_replay/tactic_replay.elisa` checks tactic kernel steps/traces; the CLI requires final state and proof-certificate replay before reporting a solved source target (`src/app/report_output_integrated_helpers.elisa`, `src/app/theorem_output.elisa`). | Tactics/search/repair are untrusted proof-term producers. The advertised action protocol is not itself a checker. Final checked result relies on source-goal binding when present and independent certificate replay. | `scripts/test.d/01b-proof-report-and-tactic-boundaries.sh`, `scripts/test.d/06-tactics-and-lifetimes.sh`, `scripts/test_tactic_branch_regions.py`, and tactic runtime harnesses. | Optional source binding and the bridge from target identifiers to exact source obligations need a complete adversarial matrix. Tactic-state mutation, stale handles and branch context identity are not exhaustively covered. A tactic trace can be deterministic yet still implement the wrong logical transition unless every operation is justified against its replay implementation. |
| Portable theorem package | `src/app/package_output.elisa` serializes arena terms, hypotheses, conclusion, rule, statement and identity hints. `src/portable/package_reader.elisa` parses a bounded strict schema. | `src/portable/package_checker.elisa::proof_package_check_theorem` recomputes statement/fingerprint, checks root ranges/rule, and dispatches supplied hypotheses/conclusion to the same kernel APIs. Its trust output says `package_reader: trusted`, `hypotheses: adapter`, `source_correspondence: adapter`, `fingerprints: identity-hint`, `source_authenticated: false`. `src/replay_main.elisa` is the standalone entry. | Package checker does not trust a producer solver; it checks each theorem. But replay establishes only “conclusion follows from supplied hypotheses”, not that those hypotheses come from Elisa source. | `scripts/test_portable_replay.py`, `scripts/tests/portable_replay_kernel_forgeries.py`, `scripts/tests/portable_replay_package_validation.py`, `scripts/tests/test_portable_package_byte_boundaries.py`, and `scripts/tests/test_portable_package_string_budget.py`. | JSON decoder/runtime/compiler correctness remains trusted. Identity hashes are not authentication. Package theorem line/name/goal identity and source correspondence are labels, not a verified source proof. Standalone replay is intentionally weaker than source admission. |

## Logical constructor and rule mapping status

`KERNEL_INVENTORY.md` machine-checks closed sets for node kinds, typing binding kinds, certificate
rules, boundary/derived/summary trace kinds, and resource fact-free leaves. It does **not** assert
that every node producer is sound, that every source constructor is covered, or that each inference
rule has a written proof argument. The checker in `scripts/test_kernel_inventory.py` verifies set
equality, not semantic correspondence.

The current path review manually confirmed the major root dispatch in `proof_replay_certificate_with_stack`
and the parallel portable dispatch in `proof_package_replay_rule`. It did not establish exhaustive
parity across all rule names, encoder branches or call sites. The highest-risk unmapped constructors
and producer-to-checker relations are:

1. **Trusted boundary fact kinds**, especially `global-constant(-qualified)`, `function-summary`,
   `lemma-summary`, and runtime/loop/branch facts. They can introduce source-derived premises with
   no logical premises at replay, so each adapter's exact source match and semantic argument needs
   a dedicated rule-to-producer audit and mutation tests.
2. **Specialized trace roots** `resource-safety`, `effect-containment`, and `structural-safety`.
   Their source adapters decide which operations/calls/patterns enter the trace; the small replay
   root alone cannot establish completeness of the source walk.
3. **Expression encoder cases** for calls with named arguments, module-qualified scope, records and
   updates, checked indexing/get, quantifier blocks, and `unsupported`. Shape admission establishes
   well-formed arena fields, not faithful encoding of every accepted Elisa AST node or faithful
   interpretation by every proposition rule.
4. **Typed-environment and binder constructors**: `reference-value`, function/signature members,
   proposition/type/field/enum identities, and quantified binders. Type formation and shadowing
   assumptions bridge source names to kernel names; distinct, immutable binder identity is not yet
   generally established.
5. **Cross-certificate summary dependencies and reuse**. SCC/depth checks in
   `certificate_validation_integrated_helpers.elisa` prevent some cycles, but the full dependency
   graph and invalidation under rule/source changes remain open (R-008/R-009).

These are review priorities, not findings that the listed rules are unsound.

## Compiler, runtime, and solver trust boundary

- Source import is performed through the Elisa front end and AST types consumed throughout
  `src/main.elisa` / `src/app/*` / `src/proof/check/*`. This audit did not prove parser, name
  resolution, type checking, effects, borrow checking, lowering, or runtime semantics. Source
  correspondence is therefore a trust dependency for source-level claims.
- The kernel is implemented in Elisa and compiled to a native product; independent replay means a
  separate checker path/product, not proof that compiler/runtime miscompilation is impossible.
  Allocation, integer overflow, string/view lifetime, bounds checks, panic/abort semantics, target
  ABI, and unsafe/extern behavior remain compiler/runtime/platform assumptions unless modeled and
  separately checked.
- SMT/ATP is not a direct trusted rule in the routes reviewed. Arithmetic/linear search and
  tactics generate candidate derivations; only accepted kernel replay should mark ordinary claims
  proved. External solver configuration/result paths were not exhaustively traced in this audit.
- Portable replay deliberately trusts its decoder and the executable while not authenticating
  source. It must not be described as source-verified merely because `kernel == checked`.

## Tests and artifact identity

The source-mapped tests above establish selected positive/negative execution paths and protocol
invariants. They do not prove universal source-adapter completeness or checker soundness. The
focused `scripts/test_kernel_inventory.py` is an inventory-set guard, not a proof. The
2026-10-05 integrated checkpoint in
[`2026-10-05-luna-slices-integrated-validation.md`](2026-10-05-luna-slices-integrated-validation.md)
records exact compiler/runtime/product hashes and test outcomes, but explicitly reports that proof
and replay manifests came from different proof-source trees; it is diagnostic, **not** a coherent
paired-artifact identity for this audit. The P-00 exact-current note records another exact product
identity for a different investigation, with a dirty proof tree. Neither note identifies a clean,
coherent product pair built from the exact source reviewed here. No tests or build were run for this
documentation-only audit; do not attribute their results to this note.

## Explicit unknowns / next R-008 slices

1. Exhaustively enumerate every source call site of `proof_kernel_add_node`, certificate/attempt
   creation and every accepted AST encoder case; bind each to its checker branch and an adversarial
   regression. Current grep/inventory output is discovery evidence only, not completeness proof.
2. For every boundary fact kind, write the source premise, producer condition, independent replay
   re-derivation (if any), and a falsifying near-miss test. Prioritize zero-premise trusted facts.
3. State and review proof arguments for every logical inference family and specialized arithmetic,
   resource, effect and termination rule. Tie each argument to the exact implementation and
   negative control.
4. Establish a clean matched proof/replay build manifest from one immutable source snapshot and
   pin compiler, frontend, runtime, target and optimization identities; then run the mapped
   positive/adversarial path set against that pair.
5. Model or explicitly exclude unsafe/extern/runtime assumptions, compiler correctness, target
   integer semantics and failure behavior from each user-facing verification claim.
6. Add a machine-readable dependency relation from admitted root through certificate/fact traces,
   source declarations, adapters, kernel rule version, executable identity and artifact cache; test
   invalidation on each dependency change.

Until these are met, neither `KERNEL_INVENTORY.md` nor this path audit establishes a complete
transitive trust graph. R-008 remains open.
